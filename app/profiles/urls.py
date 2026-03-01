from django.urls import path #, include
from .views import *

# write your url patterns here.

app_name = "profiles"

urlpatterns = [
    # profile endpoints.
    path('pathfinderprofile/', PathfinderProfileAPIView.as_view(), name="pathfinder-profile"),
    path('enablerprofile/', EnablerProfileAPIView.as_view(), name="enabler-profile"),
    path('view-profile/<int:pk>/', PathfinderViewSet.as_view(), name="view-profile"), # endpoint for viewing pathfinder profiles by their ID

    # profile picture end point.
    path('profile/picture/', ProfilePictureAPIView.as_view(), name="profile-pic"),
    path('health/', health_check, name='health-check'),

    path('credentials/', CredentialViewSet.as_view({'get': 'list', 'post': 'create'}), name='credentials'),
    path('social-links/', SocialLinkViewSet.as_view({'get': 'list', 'post': 'create'}), name='social-links'), # new endpoint for social links
    path('social-links/<int:pk>/', SocialLinkViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='social-link-detail'), # endpoint for updating/deleting individual social links
    path('credentials/<int:pk>/', CredentialViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='credential-detail'), # endpoint for updating/deleting individual credentials
    path('enablerprofile/<int:user_id>/', PublicEnablerProfileView.as_view(), name='public-enabler-profile'), # endpoint for viewing an enabler's public profile by user ID
]