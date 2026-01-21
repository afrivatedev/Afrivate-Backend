"""
Profile model for user profiles, including Enabler and Pathfinder extra fields, social links, and credentials.
"""

import os
import uuid
from django.conf import settings
from django.db import models


def profile_image_file_path(instance, filename):
    """Generate file path for the new profile pic while still maintaining the original file extension"""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f"{uuid.uuid4()}{ext}"  # create a unique filename using uuid

    return os.path.join("profile", "profile_pics", f"user_{instance.user_id}", filename)


def certification_file_path(instance, filename):
    """Generate file path for the newly added credentials while still maintaining original file ext."""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f"{uuid.uuid4()}{ext}"  # create a unique filename using uuid

    return os.path.join(
        "profile", "pathfinder_certification", f"user_{instance.profile_id}", filename
    )


def credential_file_path(instance, filename):
    """Generate file path for the newly added credentials while still maintaining original file ext."""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f"{uuid.uuid4()}{ext}"  # create a unique filename using uuid

    return os.path.join(
        "profile", "enabler_credentials", f"user_{instance.profile_id}", filename
    )


# profiles


class EnablerProfile(models.Model):
    """model to hold extra fields for the Enabler profile"""

    profile_pic = models.ImageField(
        upload_to=profile_image_file_path, null=True, blank=True
    )
    address = models.CharField(max_length=256, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(max_length=256, null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enabler_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self):
        return self.name


class PathfinderProfile(models.Model):
    """model to hold extra fields for the pathfinder profile"""

    profile_pic = models.ImageField(
        upload_to=profile_image_file_path, null=True, blank=True
    )
    title = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=256, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(max_length=256, null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pathfinder_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_name = models.CharField(max_length=50, null=False, blank=False)
    last_name = models.CharField(max_length=50, null=False, blank=False)
    other_name = models.CharField(max_length=50, null=True, blank=True)
    skills = models.ManyToManyField("Skill", related_name="pathfinders", blank=True)
    languages = models.ManyToManyField("Language", related_name="pathfinders", blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# shared entities between pathfinders
# note that most db schema design tools do not have support for many-to-many relationships
# so the intermediary tables are not explicitly defined here
class Skill(models.Model):
    """model to hold skills for pathfinders"""

    name = models.CharField(max_length=50, null=False, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Language(models.Model):
    """model to hold languages for pathfinders, it should be predefined, the frontend should have a drop-down for it"""

    name = models.CharField(max_length=50, null=False, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# unique entities to every pathfinders
class Education(models.Model):
    """model to hold education levels for pathfinders"""

    type = models.CharField(max_length=100, null=False, blank=False)
    detail = models.CharField(max_length=256, null=True, blank=True)
    profile = models.ForeignKey(
        "PathfinderProfile", on_delete=models.CASCADE, related_name="education"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type} - {self.profile.first_name} {self.profile.last_name}"


class WorkExperience(models.Model):
    """model to hold work experiences for pathfinders"""

    title = models.CharField(max_length=100, null=False, blank=False)
    details = models.CharField(max_length=256, null=True, blank=True)
    organisation = models.CharField(max_length=100, null=True, blank=True)
    profile = models.ForeignKey(
        "PathfinderProfile", on_delete=models.CASCADE, related_name="work_experiences"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.organisation} - {self.profile.first_name} {self.profile.last_name}"


class EnablerSocialLink(models.Model):
    """table for all social links for enablers"""

    platform_url = models.URLField(max_length=256, blank=False, null=False)
    profile = models.ForeignKey(
        "EnablerProfile",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="social_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.profile.name}"


class PathfinderSocialLink(models.Model):
    """table for all social links for pathfinders"""

    platform_name = models.CharField(max_length=50, blank=False, null=False)
    platform_url = models.URLField(max_length=256, blank=False, null=False)
    profile = models.ForeignKey(
        "PathfinderProfile",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="social_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.platform_name} - {self.profile.first_name} {self.profile.last_name}"
        )


class EnablerCredential(models.Model):
    """model to handle Enabler government issued credentials."""

    name = models.CharField(max_length=100, blank=False, null=False)
    document = models.FileField(upload_to=credential_file_path, blank=False, null=False)
    is_verified = models.BooleanField(default=False)
    profile = models.ForeignKey(
        "EnablerProfile",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="credentials",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.profile.name}"


class Certification(models.Model):
    """model to handle Pathfinder government issued credentials."""

    name = models.CharField(max_length=100, blank=False, null=False)
    document = models.FileField(
        upload_to=certification_file_path, blank=False, null=False
    )
    is_verified = models.BooleanField(default=False)
    profile = models.ForeignKey(
        "PathfinderProfile",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="certifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.profile.first_name} {self.profile.last_name}"
