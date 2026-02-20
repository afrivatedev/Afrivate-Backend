from django.urls import path #, include
from .views import *
# from rest_framework.routers import DefaultRouter

# write your url patterns here.

# router = DefaultRouter()

app_name = "profiles"

urlpatterns = [
    # profile endpoints.
    path('pathfinderprofile/', PathfinderProfileAPIView.as_view(), name="pathfinder-profile"),
    path('enablerprofile/', EnablerProfileAPIView.as_view(), name="enabler-profile"),

    # profile picture end point.
    path('profile/picture/', ProfilePictureAPIView.as_view(), name="profile-pic"),

    # path('', include(router.urls)),  
]