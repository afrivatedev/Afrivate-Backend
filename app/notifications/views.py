from django.http import HttpResponse
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
        user = self.request.user
        return Notification.objects.filter(user=user) | Notification.objects.filter(user__isnull=True)