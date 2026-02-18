from django.db import models
from django.conf import settings 
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class Opportunity(models.Model):
    CATEGORY_CHOICES = [
        ('voluteering', 'Volunteering'),
        ('internship', 'Internship'),
        ('scholarship', 'Scholarship'),
        ('job', 'Job'),
        ('grant', 'Grant'),
    ]

    title = models.CharField(max_length=255, null=False, blank=False)
    opportunity_type = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='voluteering', db_index=True)
    description = models.TextField()
    link = models.URLField(null=False, blank=False)
    # location = models.CharField(max_length=255, null=True, blank=True)  # e.g Remote, On-site
    posted_at = models.DateTimeField(auto_now_add=True)
    is_open = models.BooleanField(default=True,db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_opportunities', null=True, blank=True)  # Optional: Track who created the oppurtunity e.g Enabler

    class Meta:
        ordering = ['-posted_at']
        unique_together = ('title', 'link')  # Prevent duplicate opportunities

    def __str__(self):
        return self.title
    
    def can_edit(self):
        # Allow editing only within 12 hours of posting
        return timezone.now() < self.posted_at + timedelta(hours=12)
    
class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "opportunity")  # prevents duplicate saves
    
    def __str__(self):
        return f"{self.user} → {self.opportunity.title}"
    
    

 