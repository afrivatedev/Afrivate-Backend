from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from profiles.models import Profile   

User = get_user_model()

# write your signals here.
@receiver(post_save, sender=User)
def create_user_profile_and_role(sender, instance, created, **kwargs):

    if not created:
        return

    # Assign default role if missing
    if not instance.role:
        instance.role = "pathfinder"   
        instance.save()

    # Create profile if not exists
    Profile.objects.get_or_create(user=instance)