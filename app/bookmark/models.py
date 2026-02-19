from django.db import models
from django.conf import settings 
from opportunities.models import Opportunity

# Create your models here.

class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "opportunity")  # prevents duplicate saves
    
    def __str__(self):
        return f"{self.user} → {self.opportunity.title}"
    
    

 