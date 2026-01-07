from django.db import models
from django.core.validators import EmailValidator

# Create your models here.
class WaitlistEmail(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(
        unique=True, 
        null=False, 
        blank=False, 
        db_index=True, 
        validators=[EmailValidator()]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    # verification = models.OneToOneField(
    #     EmailVerification,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='waitlist_email'
    # )

    # Metadata fields
    referral_source = models.CharField(max_length=100, null=True, blank=True)
    # is_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'waitlist_emails'
        verbose_name = 'Waitlist Email'
        verbose_name_plural = 'Waitlist Emails'