from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

# Create your models here.
class Opportunity(models.Model):
    class Category(models.TextChoices):
        VOLUNTEERING = 'volunteering', 'Volunteering'
        INTERNSHIP = 'internship', 'Internship'
        SCHOLARSHIP = 'scholarship', 'Scholarship'
        MENTORSHIP = 'mentorship', 'Mentorship'
        FELLOWSHIP = 'fellowship', 'Fellowship'
        CONTRACT = 'contract', 'Contract'
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'

    title = models.CharField(max_length=255, null=False, blank=False)
    opportunity_type = models.CharField(max_length=100, choices=Category.choices, default=Category.VOLUNTEERING, db_index=True)
    description = models.TextField()
    # For scraped listings this is the apply URL on the original site.
    link = models.URLField(max_length=1000, null=False, blank=False)
    # Set once on creation (a default rather than auto_now_add so scrapers can
    # backdate it to the date the source published the listing).
    posted_at = models.DateTimeField(default=timezone.now, editable=False)
    is_open = models.BooleanField(default=True,db_index=True)
    # Optional applicant target set by the enabler; null means no target.
    target_applicants = models.PositiveIntegerField(null=True, blank=True)
    role_skill_tags = models.JSONField(default=list, blank=True, help_text="List of skills developed in this opportunity")
    # Null for scraped listings: they have no Afrivate owner and are applied to on the source site.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_opportunities',
        null=True, blank=True,
    )  # very important for permissions and filtering

    # --- Scraped (external) listings only; all blank for opportunities posted by enablers ---
    class Field(models.TextChoices):
        TECH = 'tech', 'Tech'
        BUSINESS = 'business', 'Business'
        MARKETING = 'marketing', 'Marketing'

    # db_default keeps a database-level default on these NOT NULL columns, so code that predates
    # them (and inserts without them) keeps working while a deploy and its migration roll out.
    source = models.CharField(max_length=50, blank=True, default='', db_default='', db_index=True)  # e.g. "myjobmag"
    external_id = models.CharField(max_length=255, blank=True, default='', db_default='')  # id of the listing on the source
    organization_name = models.CharField(max_length=255, blank=True, default='', db_default='')
    location = models.CharField(max_length=255, blank=True, default='', db_default='')
    is_remote = models.BooleanField(default=False, db_default=False)
    deadline = models.DateTimeField(null=True, blank=True)
    field = models.CharField(max_length=20, choices=Field.choices, blank=True, default='', db_default='', db_index=True)
    first_scraped_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-posted_at']
        unique_together = ('title', 'link')  # Prevent duplicate opportunities
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'], condition=~models.Q(source=''),
                name='unique_scraped_opportunity',
            ),
        ]

    def __str__(self):
        return self.title
    
    @property
    def is_external(self):
        return bool(self.source)

    def can_edit(self):
        # Allow editing only within 12 hours of posting
        return timezone.now() < self.posted_at + timedelta(hours=12)
    
    def save(self, *args, **kwargs):
        # Auto-close opportunity if it's too old (optional logic)
        super().save(*args, **kwargs)