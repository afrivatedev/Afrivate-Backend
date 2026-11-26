"""Batch 5: deployment-level hardening.

1. API responses carry a strict CSP, Permissions-Policy and no-store.
2. Pages that need scripts (docs, admin) are not given the strict CSP.
3. 404 and 500 pages are JSON with no internals.
4. The public waitlist endpoint is rate limited per IP (429).
5. API docs and the DRF login are off unless ENABLE_API_DOCS is set.
6. NUM_PROXIES can be set from the environment.
"""
import importlib
from unittest import mock

from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import clear_url_caches
from rest_framework.throttling import ScopedRateThrottle

from Afrivate import error_views, security_headers

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(CACHES=LOCMEM)
class SecurityHeaderTests(TestCase):
    def setUp(self):
        caches['default'].clear()

    def test_api_response_has_strict_csp_and_no_store(self):
        r = self.client.get('/api/waitlist/')  # any /api/ path; status does not matter
        self.assertEqual(r['Content-Security-Policy'], security_headers.API_CSP)
        self.assertEqual(r['Cache-Control'], 'no-store')
        self.assertIn('camera=()', r['Permissions-Policy'])

    def test_frame_and_sniff_protection(self):
        r = self.client.get('/api/waitlist/')
        self.assertEqual(r['X-Frame-Options'], 'DENY')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['Referrer-Policy'], 'same-origin')

    def test_admin_pages_keep_their_own_policy(self):
        r = self.client.get('/admin/login/')
        self.assertNotIn('Content-Security-Policy', r)

    def test_existing_cache_control_is_not_overwritten(self):
        mw = security_headers.ApiSecurityHeadersMiddleware(
            lambda request: _response_with({'Cache-Control': 'max-age=60'})
        )
        request = mock.Mock(path='/api/anything/')
        self.assertEqual(mw(request)['Cache-Control'], 'max-age=60')


def _response_with(headers):
    from django.http import HttpResponse
    r = HttpResponse('ok')
    for k, v in headers.items():
        r[k] = v
    return r


@override_settings(CACHES=LOCMEM)
class ErrorPageTests(TestCase):
    def test_unknown_path_is_json_404(self):
        r = self.client.get('/no/such/page/')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertEqual(r.json(), {'detail': 'Not found.'})

    def test_server_error_page_has_no_internals(self):
        r = error_views.server_error(mock.Mock())
        self.assertEqual(r.status_code, 500)
        body = r.content.decode()
        self.assertNotIn('Traceback', body)
        self.assertNotIn('File "', body)
        self.assertIn('Something went wrong', body)

    def test_handlers_are_registered(self):
        from Afrivate import urls
        self.assertEqual(urls.handler404, 'Afrivate.error_views.not_found')
        self.assertEqual(urls.handler500, 'Afrivate.error_views.server_error')


@override_settings(CACHES=LOCMEM)
class WaitlistThrottleTests(TestCase):
    def setUp(self):
        caches['default'].clear()

    def test_waitlist_is_rate_limited_per_ip(self):
        rates = dict(ScopedRateThrottle.THROTTLE_RATES, waitlist_join='2/hour')
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, rates, clear=True), \
                mock.patch('waitlist.views.send_welcome_email', return_value=True):
            codes = [
                self.client.post(
                    '/api/waitlist/',
                    {'name': 'Ada', 'email': f'ada{i}@example.com'},
                    content_type='application/json',
                ).status_code
                for i in range(3)
            ]
        # The first two attempts reach the view (any non-429 result); the third is blocked.
        self.assertNotIn(429, codes[:2])
        self.assertEqual(codes[2], 429)


class WaitlistRouteTests(SimpleTestCase):
    def test_waitlist_scope_has_a_rate(self):
        self.assertIn('waitlist_join', ScopedRateThrottle.THROTTLE_RATES)


class ApiDocsToggleTests(SimpleTestCase):
    """Docs and the DRF login are only routed when ENABLE_API_DOCS is true."""

    def _reload_urls(self):
        from Afrivate import urls
        importlib.reload(urls)
        clear_url_caches()

    def _paths(self):
        from Afrivate import urls
        return {str(p.pattern) for p in urls.urlpatterns}

    def tearDown(self):
        with override_settings(ENABLE_API_DOCS=True):
            self._reload_urls()

    def test_docs_hidden_when_disabled(self):
        with override_settings(ENABLE_API_DOCS=False):
            self._reload_urls()
            paths = self._paths()
        self.assertNotIn('docs/', paths)
        self.assertNotIn('api/v1/docs/', paths)
        self.assertNotIn('api-auth/', paths)

    def test_docs_present_when_enabled(self):
        with override_settings(ENABLE_API_DOCS=True):
            self._reload_urls()
            paths = self._paths()
        self.assertIn('docs/', paths)
        self.assertIn('api/v1/docs/', paths)


class ProxySettingTests(SimpleTestCase):
    def test_num_proxies_read_from_environment(self):
        # The settings module reads NUM_PROXIES once at import, so check the parsing rule.
        import os
        from importlib import reload
        from Afrivate import settings as s
        with mock.patch.dict(os.environ, {'NUM_PROXIES': '2'}):
            reload(s)
            self.assertEqual(s.REST_FRAMEWORK.get('NUM_PROXIES'), 2)
        with mock.patch.dict(os.environ, {'NUM_PROXIES': ''}):
            reload(s)
            self.assertNotIn('NUM_PROXIES', s.REST_FRAMEWORK)
