from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from user_database.models import CustomUser, EmailVerification

from datetime import timedelta


# Throttling uses the Redis cache in production; tests run against local memory
# so they don't need a Redis instance.
TEST_CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
}


@override_settings(CACHES=TEST_CACHES)
class VerifyEmailEndpointTests(TestCase):
    """verify-email is for email links only. It has no email field and no
    login, so it must never accept a 6-digit OTP or a password-reset record.
    Otherwise anyone can guess codes across all pending records and take over
    an account through the password-reset flow."""

    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='jane', email='jane@example.com',
            password='OldPass123!', role='pathfinder',
            is_email_verified=True,
        )
        self.url = reverse('accounts:verify-email')
        self.reset_url = reverse('accounts:reset-password')

    def _reset_otp(self):
        return EmailVerification.create_otp_verification(
            email=self.user.email,
            verification_type='password_reset',
            user=self.user,
        )

    def test_rejects_password_reset_otp(self):
        verification, otp = self._reset_otp()
        response = self.client.post(self.url, {'token': otp}, format='json')
        self.assertEqual(response.status_code, 400)
        verification.refresh_from_db()
        self.assertFalse(verification.is_verified)

    def test_takeover_chain_is_blocked(self):
        """The full attack: verify via verify-email, then reset with the OTP."""
        verification, otp = self._reset_otp()

        self.client.post(self.url, {'token': otp}, format='json')
        response = self.client.post(self.reset_url, {
            'token': otp,
            'new_password': 'Hacked789!',
            'confirm_password': 'Hacked789!',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_reset_rejects_six_digit_token_even_if_marked_verified(self):
        """Defence in depth: the reset endpoint itself refuses an OTP-shaped
        token, even if another code path flipped its record to verified."""
        verification, otp = self._reset_otp()
        verification.mark_verified()
        response = self.client.post(self.reset_url, {
            'token': otp,
            'new_password': 'Hacked789!',
            'confirm_password': 'Hacked789!',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_rejects_signup_otp(self):
        """A pending signup OTP must not be guessable here either."""
        pending = CustomUser.objects.create_user(
            username='sam', email='sam@example.com',
            password='OldPass123!', role='pathfinder',
            is_email_verified=False,
        )
        verification, otp = EmailVerification.create_otp_verification(
            email=pending.email,
            verification_type='user_signup',
            user=pending,
        )
        response = self.client.post(self.url, {'token': otp}, format='json')
        self.assertEqual(response.status_code, 400)
        pending.refresh_from_db()
        self.assertFalse(pending.is_email_verified)

    def test_rejects_password_reset_record_even_with_link_shaped_token(self):
        verification = EmailVerification.create_verification(
            email=self.user.email,
            verification_type='password_reset',
            user=self.user,
        )
        response = self.client.post(
            self.url, {'token': verification.token}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        verification.refresh_from_db()
        self.assertFalse(verification.is_verified)

    def test_accepts_valid_waitlist_link_token(self):
        """Regression: the real waitlist confirmation link must still work."""
        verification = EmailVerification.create_verification(
            email='early@example.com',
            verification_type='waitlist',
        )
        response = self.client.post(
            self.url, {'token': verification.token}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)

    def test_verify_email_is_rate_limited(self):
        for _ in range(30):
            response = self.client.post(
                self.url, {'token': 'f' * 32}, format='json'
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(self.url, {'token': 'f' * 32}, format='json')
        self.assertEqual(response.status_code, 429)


@override_settings(CACHES=TEST_CACHES)
class PasswordResetFlowTests(TestCase):
    """The reset endpoint must be authorized only by the single-use token
    issued at OTP verification — never by uid, and never more than once."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='jane', email='jane@example.com',
            password='OldPass123!', role='pathfinder',
            is_email_verified=True,
        )
        self.verify_url = reverse('accounts:verify-password-reset-otp')
        self.reset_url = reverse('accounts:reset-password')

    def _verified_reset_token(self):
        """Run the OTP-verify step and return the issued reset token."""
        verification, otp = EmailVerification.create_otp_verification(
            email=self.user.email,
            verification_type='password_reset',
            user=self.user,
        )
        response = self.client.post(
            self.verify_url, {'email': self.user.email, 'otp': otp}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_verify_otp_returns_single_use_token(self):
        data = self._verified_reset_token()
        self.assertIn('token', data)
        self.assertEqual(data['uid'], self.user.pk)
        # The OTP record was rotated: the original 6-digit code no longer exists.
        self.assertFalse(
            EmailVerification.objects.filter(token__regex=r'^\d{6}$').exists()
        )

    def test_reset_succeeds_with_token_and_consumes_it(self):
        token = self._verified_reset_token()['token']
        response = self.client.post(self.reset_url, {
            'token': token,
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

        # Replaying the same token must fail — it was consumed.
        replay = self.client.post(self.reset_url, {
            'token': token,
            'new_password': 'Hacked789!',
            'confirm_password': 'Hacked789!',
        }, format='json')
        self.assertEqual(replay.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_reset_rejects_uid_only_request(self):
        """A uid without a token must never authorize a reset, even when a
        historically verified reset record exists for that user."""
        self._verified_reset_token()  # user now has a verified reset record
        response = self.client.post(self.reset_url, {
            'uid': self.user.pk,
            'new_password': 'Hacked789!',
            'confirm_password': 'Hacked789!',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_reset_rejects_expired_token(self):
        token = self._verified_reset_token()['token']
        EmailVerification.objects.filter(token=token).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.post(self.reset_url, {
            'token': token,
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_reset_rejects_unverified_otp_as_token(self):
        """A raw, never-verified OTP must not work as a reset token."""
        verification, otp = EmailVerification.create_otp_verification(
            email=self.user.email,
            verification_type='password_reset',
            user=self.user,
        )
        response = self.client.post(self.reset_url, {
            'token': otp,
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, 400)
