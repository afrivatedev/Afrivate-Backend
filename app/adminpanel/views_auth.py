from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .authentication import (
    ADMIN_REFRESH_COOKIE,
    AdminJWTAuthentication,
    admin_from_payload,
    clear_admin_cookies,
    decode_admin_token,
    issue_admin_tokens,
    require_admin_request,
    set_admin_cookies,
)
from Authentication.lockout import (
    LOCKOUT_MESSAGE,
    clear_failed_attempts,
    is_locked_out,
    record_failed_attempt,
)

from .models import AdminUser
from .permissions import IsAdminPanelUser
from .serializers import AdminLoginSerializer, AdminUserSerializer


class AdminLoginView(APIView):
    """Sets the session cookies. Tokens are never returned in the response body."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_login'

    def post(self, request):
        require_admin_request(request)
        data = request.data if hasattr(request.data, 'get') else {}
        identifier = str(data.get('email') or '').strip().lower()
        # Locked per admin account, not per IP, so a spoofed X-Forwarded-For does not reset it.
        if is_locked_out('admin', identifier):
            return Response({'detail': LOCKOUT_MESSAGE}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = AdminLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except exceptions.ValidationError:
            record_failed_attempt('admin', identifier)
            raise
        clear_failed_attempts('admin', identifier)
        admin = serializer.validated_data['admin']

        admin.last_login = timezone.now()
        admin.save(update_fields=['last_login'])

        response = Response({'admin': AdminUserSerializer(admin).data})
        return set_admin_cookies(response, issue_admin_tokens(admin))


class AdminTokenRefreshView(APIView):
    """Renews the session cookies from the refresh cookie."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        require_admin_request(request)
        raw = request.COOKIES.get(ADMIN_REFRESH_COOKIE)
        if not raw:
            return Response({'detail': 'Session expired. Please sign in again.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = decode_admin_token(raw, 'admin_refresh')
            admin = admin_from_payload(payload)
        except exceptions.AuthenticationFailed as exc:
            return Response({'detail': str(exc.detail)}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response({'admin': AdminUserSerializer(admin).data})
        return set_admin_cookies(response, issue_admin_tokens(admin))


class AdminLogoutView(APIView):
    """Ends the session everywhere: bumps token_version so every issued token stops working."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        require_admin_request(request)
        raw = request.COOKIES.get(ADMIN_REFRESH_COOKIE)
        if raw:
            try:
                payload = decode_admin_token(raw, 'admin_refresh')
                admin = AdminUser.objects.get(id=payload.get('admin_id'))
                admin.token_version += 1
                admin.save(update_fields=['token_version'])
            except (exceptions.AuthenticationFailed, AdminUser.DoesNotExist, ValueError, TypeError):
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return clear_admin_cookies(response)


class AdminMeView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAdminPanelUser]

    def get(self, request):
        return Response(AdminUserSerializer(request.user).data)
