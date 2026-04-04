from django.db import models
from django.conf import settings 
from opportunities.models import Opportunity
from profiles.models import PathfinderProfileExtra

# Create your models here.
class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "opportunity")  # prevents duplicate saves
    
    def __str__(self):
        return f"{self.user} → {self.opportunity.title}"

class BookmarkUser(models.Model):
    enabler = models.ForeignKey(     # the person bookmarking a user
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='bookmarked_pathfinders'
    )
    
    pathfinder = models.ForeignKey(      # the person being bookmarked
        PathfinderProfileExtra, 
        on_delete=models.CASCADE, 
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("enabler", "pathfinder")  # prevents duplicate bookmarks

    def __str__(self):
        return f"{self.enabler} → {self.pathfinder}"