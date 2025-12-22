from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings

from django.core.validators import EmailValidator

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('enabler', 'Enabler'),
        ('pathfinder', 'Pathfinder'),
    )
    email = models.EmailField(unique=True, validators=[EmailValidator()], null=False, blank=False, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=False)
    bio = models.TextField(blank=True, null=True)
    
    # verifying email
    is_email_verified = models.BooleanField(default=False)

    # Field to store the OTP secret key
    # otp_secret_key = models.CharField(max_length=32, null=True, blank=True)
    reset_password_otp = models.IntegerField(null=True, blank=True)
    reset_password_otp_expiry = models.DateTimeField(null=True, blank=True)
    reset_password_otp_used = models.BooleanField(default=False)

    # USERNAME_FIELD = 'email_or_username' # i cant do this in abstract user
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'role']

    def tokens(self):
        """somewhere in the jwt code, there is a table storing these code alongside the attached
        custom claims"""
        refresh = RefreshToken.for_user(self)

        # attach custom claims
        refresh['role'] = self.role
        refresh['email'] = self.email

        return {
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token),
        }

    def __str__(self):
        return self.username

class OtpToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # Check if the OTP is still valid (e.g., within the last 10 minutes)
        return timezone.now() - self.created_at <= timezone.timedelta(minutes=10)

    def is_expired(self):
        # Check if the OTP has expired (e.g., after 10 minutes)
        expiration_time = timezone.now() - self.created_at
        return expiration_time > timezone.timedelta(minutes=10)

    def mark_as_used(self):
        self.is_used = True
        self.save()

    def mark_as_expired(self):
        self.expired = True
        self.save()

    def __str__(self):
        return f"OTP for {self.user.username}: {self.otp}"
    
class WaitlistEmail(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    referral_source = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True, null=False, blank=False, db_index=True, validators=[EmailValidator()])
    created_at = models.DateTimeField(auto_now_add=True)

    # is_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'waitlist_emails'
        verbose_name = 'Waitlist Email'
        verbose_name_plural = 'Waitlist Emails'