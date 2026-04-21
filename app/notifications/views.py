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
        # Short-circuit for Swagger/drf-yasg
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        user = self.request.user

        if user.is_authenticated:
            # Return notifications addressed to this user OR broadcast (recipient=None)
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

        # Unauthenticated: broadcast-only (all endpoints require auth anyway)
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
        notifications = Notification.objects.exclude(read_by=request.user)
        count = notifications.count()
        for notification in notifications:
            notification.read_by.add(request.user)
        return Response(
            {"message": f"{count} notifications marked as read."},
            status=status.HTTP_200_OK
        )