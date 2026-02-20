from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile
import logging

logger = logging.getLogger(__name__)

# write your signal handlers here. For example, you can create a user profile when a new user is created.

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Creating profile for new user: {instance.username} (ID: {instance.id})")
        Profile.objects.create(
            user=instance,
            contact_email=instance.email,
            address="",
            # city="",
            state="",
            country="",
        )

        if instance.role == "enabler":
            logger.info(f"Creating EnablerProfileExtra for user: {instance.username} (ID: {instance.id})")
            from .models import EnablerProfileExtra
            EnablerProfileExtra.objects.create(
                profile=instance.profile,
                name=instance.username,
            )
        elif instance.role == "pathfinder":
            logger.info(f"Creating PathfinderProfileExtra for user: {instance.username} (ID: {instance.id})")
            from .models import PathfinderProfileExtra
            PathfinderProfileExtra.objects.create(
                profile=instance.profile,
                first_name=instance.first_name or "",  
                last_name=instance.last_name or ""
            )

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    # This handles cases where the user is updated, ensuring the profile exists
    if hasattr(instance, 'profile'):
        logger.info(f"Saving profile for user: {instance.username} (ID: {instance.id})")
        instance.profile.save()