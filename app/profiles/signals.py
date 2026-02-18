from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

# write your signal handlers here. For example, you can create a user profile when a new user is created.

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            address="",
            city="",
            state="",
            country="",
            contact_email=instance.email
        )

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    # This handles cases where the user is updated, ensuring the profile exists
    if hasattr(instance, 'profile'):
        instance.profile.save()