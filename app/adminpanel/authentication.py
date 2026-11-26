"""
Standalone JWT auth for AdminUser (PRD 8.1).

Deliberately not simplejwt: platform tokens carry token_type "access"/"refresh"
and a user_id claim resolved against CustomUser; admin tokens carry
"admin_access"/"admin_refresh" and an admin_id resolved against AdminUser.
Neither token type is accepted by the other stack.

Browser sessions: the admin dashboard never holds its tokens in JavaScript.
Login and refresh set HttpOnly cookies; the browser sends them back on
/api/admin/ requests. Because cookies are sent automatically, every unsafe
request that authenticates with a cookie must also carry the custom
X-Admin-Request header and an allowed Origin. Browsers only send a custom
header after a CORS preflight, which the backend answers only for allowed
origins, so a request from another site cannot pass this check.

Logout (and any future revocation) bumps AdminUser.token_version. Tokens carry
the version they were issued with, so every earlier token stops working at once.
"""

from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import AdminUser

ADMIN_ACCESS_LIFETIME = timedelta(hours=1)
ADMIN_REFRESH_LIFETIME = timedelta(hours=12)
ALGORITHM = 'HS256'

ADMIN_ACCESS_COOKIE = 'afrivate_admin_access'
ADMIN_REFRESH_COOKIE = 'afrivate_admin_refresh'
ADMIN_REFRESH_PATH = '/api/admin/auth/'
ADMIN_COOKIE_PATH = '/api/admin/'
ADMIN_REQUEST_HEADER = 'HTTP_X_ADMIN_REQUEST'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


def _make_token(admin, token_type, lifetime):
    now = timezone.now()
    payload = {
        'token_type': token_type,
        'admin_id': str(admin.id),
        'email': admin.email,
        'ver': admin.token_version,
        'iat': int(now.timestamp()),
        'exp': int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def issue_admin_tokens(admin):
    return {
        'access_token': _make_token(admin, 'admin_access', ADMIN_ACCESS_LIFETIME),
        'refresh_token': _make_token(admin, 'admin_refresh', ADMIN_REFRESH_LIFETIME),
    }


def decode_admin_token(raw_token, expected_type):
    try:
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed('Token has expired.')
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed('Invalid token.')

    if payload.get('token_type') != expected_type:
        raise exceptions.AuthenticationFailed('Invalid token type.')
    return payload


def admin_from_payload(payload):
    try:
        admin = AdminUser.objects.get(id=payload.get('admin_id'))
    except (AdminUser.DoesNotExist, ValueError, TypeError):
        raise exceptions.AuthenticationFailed('Admin account not found.')
    if not admin.is_active:
        raise exceptions.AuthenticationFailed('Admin account is disabled.')
    if payload.get('ver') != admin.token_version:
        raise exceptions.AuthenticationFailed('Session has ended. Please sign in again.')
    return admin


def require_admin_request(request):
    """CSRF guard for cookie-based admin requests.

    The custom header cannot be sent by a plain cross-site form, and the Origin
    must be one of our allowed origins when the browser sends it.
    """
    if not request.META.get(ADMIN_REQUEST_HEADER):
        raise exceptions.PermissionDenied('Request check failed.')
    origin = request.META.get('HTTP_ORIGIN')
    if origin and origin not in settings.CORS_ALLOWED_ORIGINS:
        raise exceptions.PermissionDenied('Request check failed.')


def _cookie_options(max_age, path):
    return {
        'max_age': int(max_age.total_seconds()),
        'path': path,
        'secure': True,
        'httponly': True,
        # None allows the cookie on the cross-site admin-to-API call used in
        # production; Secure is required with None. See SECURITY.md.
        'samesite': getattr(settings, 'ADMIN_COOKIE_SAMESITE', 'None'),
    }


def set_admin_cookies(response, tokens):
    response.set_cookie(
        ADMIN_ACCESS_COOKIE, tokens['access_token'],
        **_cookie_options(ADMIN_ACCESS_LIFETIME, ADMIN_COOKIE_PATH),
    )
    response.set_cookie(
        ADMIN_REFRESH_COOKIE, tokens['refresh_token'],
        **_cookie_options(ADMIN_REFRESH_LIFETIME, ADMIN_REFRESH_PATH),
    )
    return response


def clear_admin_cookies(response):
    response.delete_cookie(ADMIN_ACCESS_COOKIE, path=ADMIN_COOKIE_PATH, samesite='None')
    response.delete_cookie(ADMIN_REFRESH_COOKIE, path=ADMIN_REFRESH_PATH, samesite='None')
    return response


class AdminJWTAuthentication(authentication.BaseAuthentication):
    """Authenticates an admin from the session cookie, or from `Authorization: Bearer`."""

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if header:
            if header[0].lower() != b'bearer' or len(header) != 2:
                raise exceptions.AuthenticationFailed('Invalid Authorization header.')
            payload = decode_admin_token(header[1].decode(), 'admin_access')
            return (admin_from_payload(payload), None)

        raw = request.COOKIES.get(ADMIN_ACCESS_COOKIE)
        if not raw:
            return None

        if request.method not in SAFE_METHODS:
            require_admin_request(request)

        payload = decode_admin_token(raw, 'admin_access')
        return (admin_from_payload(payload), None)

    def authenticate_header(self, request):
        return 'Bearer'
