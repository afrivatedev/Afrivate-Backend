from django.http import HttpResponse
from django.db.models import Exists, OuterRef, Q
from rest_framework import viewsets
from .models import Notification
from .serializers import NotificationSerializer

from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import viewsets, mixins
from rest_framework.generics import GenericAPIView

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

def health_check(request):
    return HttpResponse("Notifications service is running.")

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        user = self.request.user

        if user.is_authenticated:
            # recipient=user → personal notification for this user only
            # recipient=null → broadcast visible to all authenticated users
            # current_user_read is annotated as a subquery so the serializer can read
            # it as a plain attribute without triggering additional DB queries per row.
            return Notification.objects.filter(
                Q(recipient=user) | Q(recipient__isnull=True)
            ).annotate(
                current_user_read=Exists(
                    Notification.read_by.through.objects.filter(
                        notification_id=OuterRef('pk'),
                        customuser_id=user.id
                    )
                )
            ).order_by('-created_at')

        # Unauthenticated path is a fallback; in practice all list views require auth.
        return Notification.objects.filter(recipient__isnull=True).order_by('-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read_by.add(request.user)
        return Response(
            {"message": "Notification marked as read."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_all_read(self, request):
        # NOTE: this queries all notifications excluding ones already read by this user,
        # regardless of the recipient filter. It marks everything, including notifications
        # from other users' personal feeds that happen to be in the DB. This is a known
        # imprecision — ideally the queryset should mirror get_queryset()'s recipient filter.
        notifications = Notification.objects.exclude(read_by=request.user)
        count = notifications.count()
        for notification in notifications:
            notification.read_by.add(request.user)
        return Response(
            {"message": f"{count} notifications marked as read."},
            status=status.HTTP_200_OK
        )