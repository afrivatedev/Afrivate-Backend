from django.http import HttpResponse
from django.db.models import Exists, OuterRef
from rest_framework import viewsets
from .models import Notification
from .serializers import NotificationSerializer

# Create your views here.
def health_check(request):
    return HttpResponse("Notifications service is running.")

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

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
                    Notification.read_by.through.objects.filter(
                        notification_id=OuterRef('pk'),
                        user_id=user.id
                    )
                )
            ).order_by('-created_at')

        # If they aren't logged in, just show the notifications
        return Notification.objects.all().order_by('-created_at')