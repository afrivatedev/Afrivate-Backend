from django.db import models
from django.conf import settings

# Create your models here.
class Notification(models.Model):
    TYPE_CHOICES = [
        ('system', 'System'),
        ('server', 'Server'),
        ('personal', 'Personal'),
    ]

    PRIORITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="If set, only this user sees the notification. Null = broadcast to all users."
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=False, null=True)

    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='info')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='personal')

    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='read_notifications')

    def __str__(self):
        return self.title