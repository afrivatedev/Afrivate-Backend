from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile
import logging

logger = logging.getLogger(__name__)

# write your signal handlers here. For example, you can create a user profile when a new user is created.
# This is the single source of truth for profile initialisation.
# user_database/signals.py is intentionally empty — a previous version had a duplicate
# post_save handler there that called instance.save() inside the signal, causing an
# infinite loop. All profile creation logic lives here and only here.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_user_profile_and_role(sender, instance, created, **kwargs):
    if created:
        # Role fallback for social/Google signups where role might not be set yet.
        # QuerySet.update() writes directly to the DB without triggering post_save again,
        # avoiding a recursive signal loop.
        if not instance.role:
            sender.objects.filter(pk=instance.pk).update(role="pathfinder")
            instance.role = "pathfinder"

        # get_or_create ensures idempotency — safe to call multiple times without
        # duplicating profiles (e.g. if a signal fires twice due to a race condition).
        profile, p_created = Profile.objects.get_or_create(
            user=instance,
            defaults={
                "contact_email": instance.email,
                "address": "",
                "state": "",
                "country": "",
            }
        )

        # Create the role-specific extension record with safe defaults so that
        # a GET on the profile endpoint always returns a valid object, even before
        # the user fills in their profile form.
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
       
