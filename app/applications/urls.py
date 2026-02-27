from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, health_check

router = DefaultRouter()
router.register(r'', ApplicationViewSet, basename='application')

urlpatterns = [
    path("health_check/", health_check, name="application-health-check"),
    path('', include(router.urls)),
]