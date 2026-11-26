"""Batch 6: Google sign-in checks, removed token route, general per-IP limit, CORS list.

1. Google sign-in refuses an email that Google has not verified.
2. Suspended or inactive accounts get no tokens through Google.
3. An unverified password account is taken over safely: the old password stops working.
4. The plain token/ login route is gone (no limit, no verified or active checks).
5. Anonymous requests share a general per-IP limit (429).
6. The live sites are in the CORS list.
"""
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from user_database.models import CustomUser

TEST_CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def google_info(email='newbie@example.com', verified=True, **extra):
    info = {
        'iss': 'https://accounts.google.com',
        'email': email,
        'email_verified': verified,
        'given_name': 'New',
        'family_name': 'Bie',
    }
    info.update(extra)
    return info


@override_settings(CACHES=TEST_CACHES)
class GoogleLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = reverse('accounts:google-pathfinder')

    def _login(self, info):
        with mock.patch('user_database.serializers.id_token.verify_oauth2_token', return_value=info):
            return self.client.post(self.url, {'token': 'fake-google-token'}, format='json')

    def test_unverified_google_email_is_refused(self):
        r = self._login(google_info(verified=False))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(email='newbie@example.com').exists())

    def test_missing_verified_flag_is_refused(self):
        info = google_info()
        del info['email_verified']
        self.assertEqual(self._login(info).status_code, 400)

    def test_verified_new_user_is_created(self):
        r = self._login(google_info())
        self.assertEqual(r.status_code, 200)
        user = CustomUser.objects.get(email='newbie@example.com')
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.auth_provider, 'google')
        self.assertIn('access', r.data)

    def test_email_case_does_not_create_a_second_account(self):
        CustomUser.objects.create_user(
            username='jane', email='jane@example.com', password='OldPass123!',
            role='pathfinder', is_email_verified=True,
        )
        r = self._login(google_info(email='Jane@Example.com'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CustomUser.objects.filter(email__iexact='jane@example.com').count(), 1)

    def test_suspended_account_gets_no_tokens(self):
        user = CustomUser.objects.create_user(
            username='sus', email='sus@example.com', password='OldPass123!',
            role='pathfinder', is_email_verified=True,
        )
        user.is_suspended = True
        user.is_active = False
        user.save()
        r = self._login(google_info(email='sus@example.com'))
        self.assertEqual(r.status_code, 403)
        self.assertNotIn('access', r.data)

    def test_unverified_password_account_loses_its_password(self):
        """Someone may have registered this address with a password and never verified it.
        Once Google proves the real owner, that password must stop working."""
        user = CustomUser.objects.create_user(
            username='victim', email='victim@example.com', password='AttackerPass123!',
            role='pathfinder', is_email_verified=False,
        )
        r = self._login(google_info(email='victim@example.com'))
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.check_password('AttackerPass123!'))


@override_settings(CACHES=TEST_CACHES)
class TokenRouteRemovedTests(TestCase):
    def test_plain_token_login_route_is_gone(self):
        user = CustomUser.objects.create_user(
            username='u1', email='u1@example.com', password='GoodPass123!',
            role='pathfinder', is_email_verified=False,
        )
        r = APIClient().post(
            '/api/auth/token/', {'email': user.email, 'password': 'GoodPass123!'}, format='json'
        )
        self.assertEqual(r.status_code, 404)

    def test_refresh_route_still_exists(self):
        self.assertEqual(reverse('accounts:token_refresh'), '/api/auth/token/refresh/')


class _PublicPing(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'ok': True})


@override_settings(CACHES=TEST_CACHES)
class AnonymousLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_default_classes_include_anon_throttle(self):
        classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        self.assertIn('rest_framework.throttling.AnonRateThrottle', classes)
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['anon'], '100/minute')

    def test_anonymous_requests_hit_429_after_the_limit(self):
        rates = dict(AnonRateThrottle.THROTTLE_RATES, anon='3/minute')
        factory = APIRequestFactory()
        view = _PublicPing.as_view()
        with mock.patch.dict(AnonRateThrottle.THROTTLE_RATES, rates, clear=True):
            codes = [view(factory.get('/ping/', REMOTE_ADDR='9.9.9.9')).status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])


class CorsListTests(SimpleTestCase):
    def test_retired_origins_removed(self):
        self.assertNotIn('https://afrivate-tech.github.io', settings.CORS_ALLOWED_ORIGINS)
        self.assertNotIn(
            'https://afrivate-backend-production.up.railway.app', settings.CORS_ALLOWED_ORIGINS
        )

    def test_live_sites_are_allowed(self):
        for origin in (
            'https://afrivate.org',
            'https://www.afrivate.org',
            'https://afrivate-volunteer-dev-branch.vercel.app',
            'https://afrivate-admin-frontend.onrender.com',
        ):
            self.assertIn(origin, settings.CORS_ALLOWED_ORIGINS)
