import uuid
import os
from django.db import models
from django.conf import settings
from opportunities.models import Opportunity
from cloudinary_storage.storage import RawMediaCloudinaryStorage

def certificate_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f'{uuid.uuid4()}{ext}'
    return f'afrivate/certificates/user_{instance.engagement_record.volunteer.id}/{filename}'

class EngagementRecord(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('pending_attestation', 'Pending Attestation'),
        ('attested', 'Attested'),
        ('disputed', 'Disputed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='volunteer_engagements')
    organization = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='org_engagements')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name='engagements')
    
    role_title = models.CharField(max_length=255)
    role_skill_tags = models.JSONField(default=list, blank=True)
    
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    attested_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='attestations')
    attested_at = models.DateTimeField(null=True, blank=True)
    attestation_notes = models.TextField(null=True, blank=True)
    dispute_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.role_title} - {self.volunteer.username}"

class TaskEntry(models.Model):
    LOGGED_BY_CHOICES = [
        ('volunteer', 'Volunteer'),
        ('coordinator', 'Coordinator'),
    ]

    engagement_record = models.ForeignKey(EngagementRecord, on_delete=models.CASCADE, related_name='tasks')
    date = models.DateField()
    description = models.TextField()
    logged_by = models.CharField(max_length=20, choices=LOGGED_BY_CHOICES, default='volunteer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        return f"Task on {self.date} for {self.engagement_record.role_title}"

class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement_record = models.OneToOneField(EngagementRecord, on_delete=models.CASCADE, related_name='certificate')
    
    skill_summary_text = models.TextField(null=True, blank=True)
    
    # Store the actual PDF file
    pdf_file = models.FileField(storage=RawMediaCloudinaryStorage(), upload_to=certificate_file_path, null=True, blank=True)
    
    verification_page_url = models.URLField(max_length=500, null=True, blank=True)
    
    revoked = models.BooleanField(default=False)
    revoked_reason = models.TextField(null=True, blank=True)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Certificate for {self.engagement_record.volunteer.username} - {self.engagement_record.role_title}"
