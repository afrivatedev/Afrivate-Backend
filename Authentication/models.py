from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('enabler', 'Enabler'),
        ('pathfinder', 'Pathfinder'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # bio = models.TextField(blank=True, null=True)
    # profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Field to store the OTP secret key
    # otp_secret_key = models.CharField(max_length=32, null=True, blank=True)


    def __str__(self):
        return self.username
    
    def tokens(self):
        refresh_token = RefreshToken.for_user(self)
        return {
            "refresh_token": str(refresh_token),
            "access_token": str(refresh_token.access_token)
            }