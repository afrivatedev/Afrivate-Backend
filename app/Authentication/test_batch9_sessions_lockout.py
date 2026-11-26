"""Batch 9: sign out other sessions on reset or change, per-account sign-in
lockout (user and admin), and admin logging of profile views and exports.

1. Changing the password signs out every refresh token issued to the account.
2. Resetting the password signs out every refresh token issued to the account.
3. Five wrong passwords lock the account for about 15 minutes, even from a new IP.
4. A correct sign-in clears the failure count.
5. The same lockout applies to admin sign-in.
6. Opening a user's profile, and exporting the user list, are recorded.
"""
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from adminpanel.models import AdminActionLog, AdminUser, EntityType
from user_database.models import CustomUser, EmailVerification

OLD_PASSWORD = 'OldPass123!'
NEW_PASSWORD = 'NewPass456!xyz'


def make_user(email='person@example.com'):
    return CustomUser.objects.create_user(
        username=email.split('@')[0], email=email, password=OLD_PASSWORD,
        role='pathfinder', is_email_verified=True,
    )


class SessionRevocationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.refresh = self.user.tokens()['refresh_token']
        self.client = APIClient()

    def _refresh_status(self):
        return self.client.post(reverse('accounts:token_refresh'), {'refresh': self.refresh}, format='json').status_code

    def test_change_password_signs_out_existing_refresh_tokens(self):
        self.assertEqual(self._refresh_status(), status.HTTP_200_OK)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('accounts:change-password'), {
            'old_password': OLD_PASSWORD, 'new_password': NEW_PASSWORD, 'confirm_password': NEW_PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=None)
        self.assertEqual(self._refresh_status(), status.HTTP_401_UNAUTHORIZED)

    def test_reset_password_signs_out_existing_refresh_tokens(self):
        token = uuid.uuid4().hex  # link tokens are 32 hex characters
        EmailVerification.objects.create(
            user=self.user, email=self.user.email, token=token, verification_type='password_reset',
            is_verified=True, expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertEqual(self._refresh_status(), status.HTTP_200_OK)
        response = self.client.post(reverse('accounts:reset-password'), {
            'token': token, 'new_password': NEW_PASSWORD, 'confirm_password': NEW_PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._refresh_status(), status.HTTP_401_UNAUTHORIZED)


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class UserLoginLockoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user('locked@example.com')
        self.url = reverse('accounts:login')

    def _login(self, password, ip='10.0.0.1'):
        return APIClient().post(
            self.url, {'username_or_email': 'locked@example.com', 'password': password},
            format='json', REMOTE_ADDR=ip,
        )

    def test_five_wrong_passwords_lock_the_account(self):
        for _ in range(5):
            self.assertEqual(self._login('wrong-guess').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._login(OLD_PASSWORD).status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_lock_follows_the_account_not_the_ip(self):
        for i in range(5):
            self._login('wrong-guess', ip=f'10.1.0.{i + 1}')
        self.assertEqual(self._login(OLD_PASSWORD, ip='203.0.113.9').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_sign_in_clears_the_failure_count(self):
        for _ in range(3):
            self._login('wrong-guess')
        self.assertEqual(self._login(OLD_PASSWORD).status_code, status.HTTP_200_OK)
        for _ in range(4):
            self.assertEqual(self._login('wrong-guess').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._login(OLD_PASSWORD).status_code, status.HTTP_200_OK)

    def test_other_accounts_are_not_locked(self):
        for _ in range(5):
            self._login('wrong-guess')
        make_user('someone.else@example.com')
        response = APIClient().post(
            self.url, {'username_or_email': 'someone.else@example.com', 'password': OLD_PASSWORD},
            format='json', REMOTE_ADDR='10.0.0.2',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class AdminLoginLockoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = AdminUser.objects.create(full_name='Admin One', email='admin@afrivate.test')
        self.admin.set_password('AdminPass789!')
        self.admin.save()
        self.url = reverse('admin-login')

    def _login(self, password, ip='10.0.0.1'):
        return APIClient().post(
            self.url, {'email': 'admin@afrivate.test', 'password': password},
            format='json', HTTP_X_ADMIN_REQUEST='1', REMOTE_ADDR=ip,
        )

    def test_five_wrong_passwords_lock_the_admin_account(self):
        for _ in range(5):
            self.assertEqual(self._login('wrong-guess').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._login('AdminPass789!').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_spoofed_forwarded_header_does_not_reset_the_lock(self):
        for i in range(5):
            APIClient().post(
                self.url, {'email': 'admin@afrivate.test', 'password': 'wrong-guess'},
                format='json', HTTP_X_ADMIN_REQUEST='1', HTTP_X_FORWARDED_FOR=f'198.51.100.{i + 1}',
            )
        response = APIClient().post(
            self.url, {'email': 'admin@afrivate.test', 'password': 'AdminPass789!'},
            format='json', HTTP_X_ADMIN_REQUEST='1', HTTP_X_FORWARDED_FOR='198.51.100.99',
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AdminLoggingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = AdminUser.objects.create(full_name='Admin One', email='admin@afrivate.test')
        self.person = make_user('profile.check@example.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_viewing_a_user_profile_is_logged(self):
        response = self.client.get(reverse('admin-user-detail', args=[self.person.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = AdminActionLog.objects.get(action_type=AdminActionLog.ActionType.VIEW_PROFILE)
        self.assertEqual(entry.admin_id, self.admin.id)
        self.assertEqual(entry.target_entity_type, EntityType.USER)
        self.assertEqual(entry.target_entity_id, str(self.person.id))

    def test_csv_export_is_logged_with_row_count(self):
        response = self.client.get(reverse('admin-users') + '?export=csv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = AdminActionLog.objects.get(action_type=AdminActionLog.ActionType.EXPORT)
        self.assertEqual(entry.admin_id, self.admin.id)
        self.assertIn('CSV export of 1 users', entry.reason)
