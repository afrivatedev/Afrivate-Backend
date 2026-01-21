"""
Url  file for the profiles page.
"""
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import (
    EnablerProfileAPIView,
    PathfinderProfileAPIView,
    ProfilePictureAPIView,
    EnablerCredentialViewSet,
    CertificationViewSet,
    EnablerSocialLinkViewSet,
    PathfinderSocialLinkViewSet,
)

router = DefaultRouter()
router.register(r'enabler/credentials', EnablerCredentialViewSet, basename='enabler-credential')
router.register(r'pathfinder/certifications', CertificationViewSet, basename='certification')
router.register(r'enabler/social-links', EnablerSocialLinkViewSet, basename='enabler-social-link')
router.register(r'pathfinder/social-links', PathfinderSocialLinkViewSet, basename='pathfinder-social-link')

app_name = "profiles"

urlpatterns = [
    # profile endpoints.
    path('pathfinderprofile/', PathfinderProfileAPIView.as_view(), name="pathfinder-profile"),
    path('enablerprofile/', EnablerProfileAPIView.as_view(), name="enabler-profile"),

    # profile picture end point.
    path('profile-picture/', ProfilePictureAPIView.as_view(), name="profile-pic"),
    path('', include(router.urls),),


]