from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('enabler', 'Enabler'),
        ('pathfinder', 'Pathfinder'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=False)
    bio = models.TextField(blank=True, null=True)
    # profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Field to store the OTP secret key
    otp_secret_key = models.CharField(max_length=32, null=True, blank=True)

    # USERNAME_FIELD = 'email_or_username' # i cant do this in abstract user
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username','role']

    def tokens(self):
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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
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