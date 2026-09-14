from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application
from engagements.models import EngagementRecord

@receiver(post_save, sender=Application)
def create_engagement_record(sender, instance, created, **kwargs):
    # Only create an engagement if the application is accepted
    if instance.status == 'accepted':
        # Check if an engagement already exists for this application to avoid duplicates
        # Since we don't have a direct Application FK in EngagementRecord, we check by volunteer and opportunity
        exists = EngagementRecord.objects.filter(
            volunteer=instance.user,
            opportunity=instance.opportunity
        ).exists()
        
        if not exists:
            EngagementRecord.objects.create(
                volunteer=instance.user,
                organization=instance.opportunity.created_by,
                opportunity=instance.opportunity,
                role_title=instance.opportunity.title,
                role_skill_tags=instance.opportunity.role_skill_tags,
                status='in_progress'
            )
