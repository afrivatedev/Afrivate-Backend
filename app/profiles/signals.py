"""
signals that handle filling of some of the user's profile immediately they sign up.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Profile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Fills out a part of the user profile using the sign up data provided, immediately
    the user signs up.
    """
    if created:
        Profile.objects.create(user=instance, email=instance.email, )