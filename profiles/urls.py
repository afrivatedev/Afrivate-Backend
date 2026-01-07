"""
Url  file for the profiles page.
"""
from django.urls import path

from profiles import views

app_name = "profiles"

urlpatterns = [
    # profile endpoints.
    path('pathfinderprofile/', views.PathfinderProfileAPIView.as_view(), name="pathfinder-profile"),
    path('enablerprofile/', views.EnablerProfileAPIView.as_view(), name="enabler-profile"),

    # profile picture end point.
    path('profile/picture/', views.ProfilePictureAPIView.as_view(), name="profile-pic"),
]