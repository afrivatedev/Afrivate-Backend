from django.urls import path
from .views import *

# write your urls here

urlpatterns = [
    path("health/", health_check, name="notification-health-check"),
    path("notifications/", NotificationViewSet.as_view({'get': 'list', 'post': 'create'}), name="notification-list-create"),
    path("notifications/<int:pk>/", NotificationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name="notification-detail"),
    path("notifications/<int:pk>/mark-read/", NotificationViewSet.as_view({ 'post': 'mark_read' }), name='notification-mark-read'),
    path("notifications/mark-all-read/", NotificationViewSet.as_view({ 'post': 'mark_all_read' }), name="notification-mark-all-read"),
]

