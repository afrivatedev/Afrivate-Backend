from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q


class BaseProfile(models.Model):
    """Base profile model"""
    profile_pic = models.ImageField(upload_to="profile_pic/", null=True, blank=True)
    address = models.TextField(max_length=256,null=False, blank=False)
    city = models.CharField(max_length=50, null=False, blank=False)
    state = models.CharField(max_length=50,null=False, blank=False)
    country = models.CharField(max_length=50,null=False, blank=False)
    email = models.EmailField(max_length=256, null=False, blank=False)
    phone_number = models.CharField(max_length=20,null=True, blank=True)
    website = models.URLField(max_length=256,null=True, blank=True)
    bio = models.TextField(max_length=150,null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class EnablerProfile(BaseProfile):
    """This is the user profile model for the Enabler"""
    name = models.CharField(max_length=100, null=True, blank=True)

class PathfinderProfile(BaseProfile):
    """This is the user profile model for the Pathfinder"""
    firstname = models.CharField(max_length=50,null=True, blank=True)
    lastname = models.CharField(max_length=50,null=True, blank=True)
    othername = models.CharField(max_length=50,null=True, blank=True)
    username = models.CharField(max_length=50,null=True, blank=True)

class SocialLink(models.Model):
    """table for all social links, it is attached to the profile instance"""
    ROLE_CHOICES = (
        ("enabler", "Enabler"),
        ("pathfinder", "Pathfinder"),
    )
    platform_name = models.CharField(max_length=50, blank=False,null=False)
    platform_url = models.URLField(max_length=150,blank=False, null=False)
    role = models.CharField(max_length=50,choices=ROLE_CHOICES, blank=False, null=False)
    enabler_profile = models.ForeignKey("EnablerProfile", on_delete=models.CASCADE,blank=True, null=True)
    pathfinder_profile = models.ForeignKey("PathfinderProfile", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        # constraint that ensures that the enabler and pathfinder column of a field must have at least one of them null
        constraints = [
            CheckConstraint(
                check=(Q(enabler_profile__isnull=True) | Q(pathfinder_profile__isnull=True)),
                name="profile_exclusivity"
            )
        ]

class Credential(models.Model):
    """model to handle both pathfinder and Enablers government issued credentials, it is attached to the user instance"""
    ROLE_CHOICES = (
        ("enabler", "Enabler"),
        ("pathfinder", "Pathfinder"),
    )
    document_name = models.CharField(max_length=100, blank=False, null=False)
    document = models.FileField(upload_to="profile/credentials/", blank=False, null=False)
    is_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=50,choices=ROLE_CHOICES, blank=False, null=False)
    enabler_profile = models.ForeignKey("EnablerProfile", on_delete=models.CASCADE,blank=True, null=True)
    pathfinder_profile = models.ForeignKey("PathfinderProfile", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        # constraint that ensures that the enabler and pathfinder column of a field must have atleat one of them null
        constraints = [
            CheckConstraint(
                check=(Q(enabler_profile__isnull=True) | Q(pathfinder_profile__isnull=True)),
                name="profile_exclusivity"
            )
        ]