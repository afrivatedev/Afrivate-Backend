from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile
import logging

logger = logging.getLogger(__name__)

# write your signal handlers here. For example, you can create a user profile when a new user is created.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_user_profile_and_role(sender, instance, created, **kwargs):
    if created:
        # 1. Handle Role Assignment (Fallback for Google/Social)
        if not instance.role:
            # Use .update to avoid re-triggering post_save
            sender.objects.filter(pk=instance.pk).update(role="pathfinder")
            instance.role = "pathfinder" 

        # 2. Create Base Profile
        profile, p_created = Profile.objects.get_or_create(
            user=instance,
            
            defaults={
                "contact_email": instance.email,
                "address": "",
                # city="",
                "state": "",
                "country": "" # Avoid null errors in prod
            }
        )

        # 3. Create Role-Specific Extras
        if instance.role == "enabler":
            logger.info(f"Creating EnablerProfileExtra for user: {instance.username} (ID: {instance.id})")
            from .models import EnablerProfileExtra
            EnablerProfileExtra.objects.get_or_create(profile=profile, defaults={"name": instance.username})
        else:
            logger.info(f"Creating PathfinderProfileExtra for user: {instance.username} (ID: {instance.id})")
            from .models import PathfinderProfileExtra
            PathfinderProfileExtra.objects.get_or_create(
                profile=profile, 
                defaults={"first_name": instance.first_name or "", "last_name": instance.last_name or "", "gmail": instance.email}
            )
       

            
# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         logger.info(f"Creating profile for new user: {instance.username} (ID: {instance.id})")
#         Profile.objects.create(
#             user=instance,
#             contact_email=instance.email,
#             address="",
#             # city="",
#             state="",
#             country="",
#         )

#         if instance.role == "enabler":
#             logger.info(f"Creating EnablerProfileExtra for user: {instance.username} (ID: {instance.id})")
#             from .models import EnablerProfileExtra
#             EnablerProfileExtra.objects.create(
#                 profile=instance.profile,
#                 name=instance.username,
#             )
#         elif instance.role == "pathfinder":
#             logger.info(f"Creating PathfinderProfileExtra for user: {instance.username} (ID: {instance.id})")
#             from .models import PathfinderProfileExtra
#             PathfinderProfileExtra.objects.create(
#                 profile=instance.profile,
#                 first_name=instance.first_name or "",  
#                 last_name=instance.last_name or "",
#                 gmail=instance.email,
#             )

# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def save_user_profile(sender, instance, **kwargs):
#     # This handles cases where the user is updated, ensuring the profile exists
#     if hasattr(instance, 'profile'):
#         logger.info(f"Saving profile for user: {instance.username} (ID: {instance.id})")
#         instance.profile.save()