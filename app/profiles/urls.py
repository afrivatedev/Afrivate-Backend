"""
Url  file for the profiles page.
"""
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from profiles import views


router = DefaultRouter()

router.register("social-link", )
router.register("credential", )
router.register("profile", )

urlpatterns = [
    path('', include(router.urls) ),

]