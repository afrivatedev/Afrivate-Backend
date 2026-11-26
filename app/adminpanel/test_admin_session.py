"""
Admin dashboard session tests.

1. Login and refresh set HttpOnly, Secure cookies and never return tokens in the body.
2. Cookie-authenticated unsafe requests need the X-Admin-Request header and an allowed Origin.
3. Logout ends every earlier session (token_version bump).
4. A volunteer-platform token is not accepted as an admin session.
5. CSV exports neutralise spreadsheet formulas.
"""
import csv
import io

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import ADMIN_ACCESS_COOKIE, ADMIN_REFRESH_COOKIE
from .models import AdminUser
from .utils import csv_response

ADMIN_HEADER = {'HTTP_X_ADMIN_REQUEST': '1'}
ALLOWED_ORIGIN = 'http://localhost:3001'
EMAIL = 'session-admin@example.com'
PASSWORD = 'SessionTest-123!'


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class AdminSessionTests(TestCase):
    def setUp(self):
        # The throttle uses the 'default' cache (LocMem under override_settings above).
        # LocMem state persists by name across tests, so clear it or logins hit the limit.
        caches['default'].clear()
        self.admin = AdminUser(full_name='Session Admin', email=EMAIL)
        self.admin.set_password(PASSWORD)
        self.admin.save()
        self.client = APIClient()

    def _login(self):
        return self.client.post(
            '/api/admin/auth/login/', {'email': EMAIL, 'password': PASSWORD},
            format='json', **ADMIN_HEADER,
        )

    # 1. cookies, not tokens in the body
    def test_login_sets_httponly_secure_cookies_and_no_tokens_in_body(self):
        response = self._login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('access_token', response.data)
        self.assertNotIn('refresh_token', response.data)
        self.assertEqual(response.data['admin']['email'], EMAIL)
        for name in (ADMIN_ACCESS_COOKIE, ADMIN_REFRESH_COOKIE):
            cookie = response.cookies[name]
            self.assertTrue(cookie['httponly'])
            self.assertTrue(cookie['secure'])
            self.assertEqual(cookie['samesite'], 'None')

    def test_login_without_request_header_is_refused(self):
        response = self.client.post(
            '/api/admin/auth/login/', {'email': EMAIL, 'password': PASSWORD}, format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_refresh_renews_cookies(self):
        self._login()
        response = self.client.post('/api/admin/auth/refresh/', {}, format='json', **ADMIN_HEADER)
        self.assertEqual(response.status_code, 200)
        self.assertIn(ADMIN_ACCESS_COOKIE, response.cookies)
        self.assertNotIn('access_token', response.data)

    # 2. cookie session works, and unsafe requests need the header
    def test_cookie_session_reads_admin_profile(self):
        self._login()
        response = self.client.get('/api/admin/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], EMAIL)

    def test_cookie_post_without_header_is_refused(self):
        self._login()
        response = self.client.post('/api/admin/notes/', {'note_text': 'x'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_cookie_post_with_header_is_processed(self):
        self._login()
        response = self.client.post(
            '/api/admin/notes/', {'note_text': 'x'}, format='json', **ADMIN_HEADER,
        )
        # Passes the CSRF check; the note itself is invalid, so validation answers.
        self.assertEqual(response.status_code, 400)

    def test_cross_site_origin_is_refused_even_with_header(self):
        self._login()
        response = self.client.post(
            '/api/admin/notes/', {'note_text': 'x'}, format='json',
            HTTP_X_ADMIN_REQUEST='1', HTTP_ORIGIN='https://evil.example',
        )
        self.assertEqual(response.status_code, 403)

    def test_allowed_origin_is_accepted(self):
        self._login()
        response = self.client.post(
            '/api/admin/notes/', {'note_text': 'x'}, format='json',
            HTTP_X_ADMIN_REQUEST='1', HTTP_ORIGIN=ALLOWED_ORIGIN,
        )
        self.assertEqual(response.status_code, 400)

    # 3. logout ends every earlier session
    def test_logout_revokes_existing_tokens(self):
        login = self._login()
        old_access = login.cookies[ADMIN_ACCESS_COOKIE].value
        old_refresh = login.cookies[ADMIN_REFRESH_COOKIE].value

        logout = self.client.post('/api/admin/auth/logout/', {}, format='json', **ADMIN_HEADER)
        self.assertEqual(logout.status_code, 204)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.token_version, 1)

        # Replay the old cookies: both must now be rejected.
        self.client.cookies[ADMIN_ACCESS_COOKIE] = old_access
        self.assertEqual(self.client.get('/api/admin/auth/me/').status_code, 401)

        self.client.cookies[ADMIN_REFRESH_COOKIE] = old_refresh
        refresh = self.client.post('/api/admin/auth/refresh/', {}, format='json', **ADMIN_HEADER)
        self.assertEqual(refresh.status_code, 401)

    def test_logout_without_header_is_refused_and_changes_nothing(self):
        self._login()
        response = self.client.post('/api/admin/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.token_version, 0)

    def test_disabled_admin_is_refused(self):
        self._login()
        self.admin.is_active = False
        self.admin.save()
        self.assertEqual(self.client.get('/api/admin/auth/me/').status_code, 401)

    # 4. platform tokens are not admin sessions
    def test_volunteer_platform_token_is_not_an_admin_session(self):
        user = get_user_model().objects.create_user(
            username='vol', email='vol@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        self.client.cookies[ADMIN_ACCESS_COOKIE] = str(RefreshToken.for_user(user).access_token)
        self.assertEqual(self.client.get('/api/admin/auth/me/').status_code, 401)

    def test_no_cookie_means_not_logged_in(self):
        self.assertEqual(self.client.get('/api/admin/users/').status_code, 401)


class CsvFormulaTests(TestCase):
    def _rows(self, response):
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_formula_cells_are_neutralised(self):
        response = csv_response('t.csv', ['name'], [
            ['=HYPERLINK("http://x")'], ['+1 555'], ['-2+3'], ['@SUM(A1)'], ['\tcmd'],
        ])
        cells = [row[0] for row in self._rows(response)[1:]]
        for cell in cells:
            self.assertTrue(cell.startswith("'"), cell)

    def test_plain_text_and_numbers_are_unchanged(self):
        response = csv_response('t.csv', ['name', 'count'], [['Ada Okafor', 7], ['Lagos', 0]])
        rows = self._rows(response)
        self.assertEqual(rows[1], ['Ada Okafor', '7'])
        self.assertEqual(rows[2], ['Lagos', '0'])
