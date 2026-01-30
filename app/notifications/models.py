from django.db import models
from django.conf import settings

# Create your models here.
class Notification(models.Model):
    SYSTEM = 'system', 'System'
    SERVER = 'server', 'Server'
    PERSONAL = 'personal', 'Personal'

    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    CRITICAL = 'critical', 'Critical'

    TYPE_CHOICES = [
        (SYSTEM),
        (SERVER),
        (PERSONAL)
    ]
         
    PRIORITY_CHOICES = [ 
        (INFO),
        (WARNING),
        (CRITICAL)
    ]
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications') # a system to link notifications to users can be added later
    title = models.CharField(max_length=200)
    message = models.TextField(blank=False, null=True)
    
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=INFO)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=SYSTEM) # this determienes if the user is required  
    
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='read_notifications')

    def __str__(self):
        return self.title