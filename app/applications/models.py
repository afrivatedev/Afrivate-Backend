from django.db import models
from django.conf import settings
from opportunities.models import Opportunity

# Create your models here.
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='applicants')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    cover_letter = models.TextField(blank=True)
    # resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # jjust to ensures that a user can only apply once per opportunity
        unique_together = ('user', 'opportunity')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.user.username} - {self.opportunity.title}"