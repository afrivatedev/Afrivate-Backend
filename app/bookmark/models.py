from django.db import models
from django.conf import settings 

# Create your models here.
class Opportunity(models.Model):
    title = models.CharField(max_length=255, null=False, blank=False)
    opportunity_type = models.CharField(max_length=100)  # e.g Internship, Scholarship, Job, Grant
    description = models.TextField()
    link = models.URLField(null=False, blank=False)
    # location = models.CharField(max_length=255, null=True, blank=True)  # e.g Remote, On-site
    posted_at = models.DateTimeField(auto_now_add=True)
    is_open = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Optional: Track who created the oppurtunity e.g Enabler

    def __str__(self):
        return self.title
    
class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "opportunity")  # prevents duplicate saves
    
    def __str__(self):
        return f"{self.user} → {self.opportunity.title}"
    
    

 