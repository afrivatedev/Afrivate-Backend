from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Feedback(models.Model):
    TYPE_CHOICES = (
        ('bug', 'Bug Report'),
        ('complaint', 'Complaint'),
        ('feature', 'Feature Request'),
        ('suggestion', 'UI/UX Suggestion'),
        ('support', 'Support Escalation'),
        ('general', 'General Feedback'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    rating = models.IntegerField(null=True, blank=True, help_text="Optional 1-5 rating")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='support/feedback_attachments/', null=True, blank=True)
    context_info = models.JSONField(null=True, blank=True, help_text="Automatically captured context like device, area, etc.")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_feedbacks', limit_choices_to={'is_staff': True})
    internal_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.subject}"

class KnowledgeBaseArticle(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="The problem or context")
    solution = models.TextField(help_text="The verified solution")
    category = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    last_reviewed = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class SupportChatSession(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    escalated_ticket = models.ForeignKey(Feedback, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_session')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} for {self.user}"

class SupportChatMessage(models.Model):
    ROLE_CHOICES = (
        ('system', 'System'),
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('human_support', 'Human Support'),
    )
    
    session = models.ForeignKey(SupportChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    attachment = models.FileField(upload_to='support/chat_attachments/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message {self.id} from {self.role}"
