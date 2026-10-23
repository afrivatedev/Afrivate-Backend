from django.db import models


class ExternalOpportunity(models.Model):
    """
    A volunteer opportunity scraped from a third-party source.

    Kept separate from `opportunities.Opportunity`, which is owned by an
    Enabler (created_by, applications, edit window). Scraped listings have no
    owner and users apply on the original site via `apply_url`.
    """

    class Field(models.TextChoices):
        TECH = 'tech', 'Tech'
        BUSINESS = 'business', 'Business'
        MARKETING = 'marketing', 'Marketing'

    class OpportunityType(models.TextChoices):
        VOLUNTEER = 'volunteer', 'Volunteer'
        INTERNSHIP = 'internship', 'Internship'

    source = models.CharField(max_length=50, db_index=True)  # e.g. "reliefweb"
    opportunity_type = models.CharField(
        max_length=20, choices=OpportunityType.choices,
        default=OpportunityType.VOLUNTEER, db_index=True,
    )
    external_id = models.CharField(max_length=255)  # id of the listing on the source
    title = models.CharField(max_length=255)
    organization_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    apply_url = models.URLField(max_length=1000)  # where the user applies
    source_url = models.URLField(max_length=1000, blank=True)  # listing page on the source
    field = models.CharField(max_length=20, choices=Field.choices, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    is_remote = models.BooleanField(default=True, db_index=True)
    deadline = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    first_scraped_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-posted_at', '-first_scraped_at']
        constraints = [
            models.UniqueConstraint(fields=['source', 'external_id'], name='unique_external_listing'),
        ]

    def __str__(self):
        return f'[{self.source}] {self.title}'
