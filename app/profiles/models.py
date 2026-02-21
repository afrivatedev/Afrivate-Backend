"""
Profile model for user profiles, including Enabler and Pathfinder extra fields, social links, and credentials.
"""

import os
import uuid
from django.conf import settings
from django.db import models

PROFILE_UPLOAD_PATH = 'profile' 

# write your models here.
def recipe_image_file_path(instance, filename):
    """Generate file path for the new profile pic while still maintaining the original file extension"""
    ext = os.path.splitext(filename)[1] # Get the file extension
    filename = f'{uuid.uuid4()}{ext}' # create a unique filename using uuid
    
    return os.path.join(PROFILE_UPLOAD_PATH, 'profile_pics', f'user_{instance.user_id}',filename)

def credential_file_path(instance, filename):
    """Generate file path for the newly added credentials while still maintaining original file ext."""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f'{uuid.uuid4()}{ext}' # create a unique filename using uuid

    return os.path.join('profile', 'credentials', f'user_{instance.user_id}', filename)


class Profile(models.Model):
    """Profile model. Base Fields shared by both Enabler and the Pathfinder"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="profile")
    profile_pic = models.ImageField(upload_to=recipe_image_file_path, null=True, blank=True)
    bio = models.TextField(max_length=150,null=True, blank=True)
    
    # contact and location
    contact_email = models.EmailField(max_length=256, null=False, blank=False)
    phone_number = models.CharField(max_length=20,null=True, blank=True)
    address = models.TextField(max_length=256,null=False, blank=False)
    # city = models.CharField(max_length=50, null=False, blank=False)
    state = models.CharField(max_length=50,null=False, blank=False)
    country = models.CharField(max_length=50,null=False, blank=False)
    
    website = models.URLField(max_length=256,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class EnablerProfileExtra(models.Model):
    """model to hold extra fields for the Enabler profile"""
    name = models.CharField(max_length=100, null=False, blank=False)
    profile = models.OneToOneField("Profile", on_delete=models.CASCADE, blank=False, null=False, related_name="enabler_extra")
    employees = models.IntegerField(null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)

class PathfinderProfileExtra(models.Model):
    """model to hold extra fields for the pathfinder profile"""
    first_name = models.CharField(max_length=50,null=False, blank=False)
    last_name = models.CharField(max_length=50,null=False, blank=False)
    other_name = models.CharField(max_length=50,null=True, blank=True)
    profile = models.OneToOneField("Profile", on_delete=models.CASCADE, blank=False, null=False, related_name="pathfinder_extra")

    title = models.CharField(max_length=100, help_text="e.g. Software Engineer, Data Scientist", null=True, blank=True)
    about = models.TextField(max_length=1000, null=True, blank=True)
    work_experience = models.TextField(blank=True)
    languages = models.CharField(max_length=200, help_text="English, French, Yoruba", null=True, blank=True)  
    gmail = models.EmailField(max_length=256, null=True, blank=True)
    

class SocialLink(models.Model):
    """table for all social links, it is attached to the profile instance"""

    platform_name = models.CharField(max_length=50, blank=False,null=False)
    platform_url = models.URLField(max_length=150,blank=False, null=False)
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE, blank=False, null=False, related_name="social_links")


class Credential(models.Model):
    """model to handle both pathfinder and Enablers government issued credentials, it is attached to the user instance"""
    document_name = models.CharField(max_length=100, blank=False, null=False)
    document = models.FileField(upload_to=credential_file_path, blank=False, null=False)
    is_verified = models.BooleanField(default=False)
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE, blank=False, null=False, related_name="credentials")


class PathfinderSkill(models.Model):
    """model to handle pathfinder skills and expertise, it is attached to the user instance"""
    name = models.CharField(max_length=100, blank=False, null=False)
    pathfinder = models.ForeignKey("PathfinderProfileExtra", on_delete=models.CASCADE, blank=False, null=False, related_name="pathfinder_skills")


class PathfinderEducation(models.Model):
    """model to handle pathfinder education details, it is attached to the user instance"""
    name = models.CharField(max_length=100, blank=False, null=False)
    pathfinder = models.ForeignKey("PathfinderProfileExtra", on_delete=models.CASCADE, blank=False, null=False, related_name="pathfinder_education")


class PathfinderCertification(models.Model):
    """model to handle pathfinder certifications, it is attached to the user instance"""
    name = models.CharField(max_length=100, blank=False, null=False)
    pathfinder = models.ForeignKey("PathfinderProfileExtra", on_delete=models.CASCADE, blank=False, null=False, related_name="pathfinder_certifications")

