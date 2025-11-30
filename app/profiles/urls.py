"""
Url  file for the profiles page.
"""
from django.urls import path

from rest_framework.routers import DefaultRouter

from profiles import views

# router = DefaultRouter()

# router.register('credentials', views.CredentialViewSet, basename='credential')
# app_name = "profiles"

urlpatterns = [
    # profile endpoins.
    path('pathfinderprofile/',views.PathfinderProfileAPIView.as_view(), name="pathfinder-profile"),
    path('enablerprofile/', views.EnablerProfileAPIView.as_view(), name="enabler-profile"),

    # profile picture end point.
    path('pathfinderprofile/profile-pic/', views.PathfinderProfilePicAPIView.as_view(), name="p-pic"),
    path('enableprofile/profile-pic/', views.EnablerProfilePicAPIView.as_view(), name= "e-pic"),

]