from django.http import HttpResponse
from django.db.models import Exists, OuterRef
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


def health_check(request):
    return HttpResponse("Notifications service is running.")

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        # Short-circuit for Swagger/drf-yasg
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        # Get the current viewer
        user = self.request.user

        # If they are logged in, check the "read_by" table for THEIR ID
        if user.is_authenticated:
            return Notification.objects.annotate(
                current_user_read=Exists(
                    Notification.objects.filter(
                        pk=OuterRef('pk'),
                        read_by=user
                    )
                )
            ).order_by('-created_at')

        # If they aren't logged in, just show the notifications
        return Notification.objects.all().order_by('-created_at')
    
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
        unread_notifications = Notification.objects.exclude(read_by=request.user)

        if unread_notifications.exists():
            request.user.read_notifications.add(*unread_notifications)

        return Response(
            {"message": "All notifications marked as read."},
            status=status.HTTP_200_OK
        )