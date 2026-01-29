from django.urls import path
from .views import *

# write your ursls here

urlpatterns = [
    path("health/", health_check, name="notification-health-check"),
    path("notifications/", NotificationViewSet.as_view({'get': 'list', 'post': 'create'}), name="notification-list-create"),
    path("notifications/<int:pk>/", NotificationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name="notification-detail"),
    
]
