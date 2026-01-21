"""
this would be a combined db for both the volunteer
opportunities and regular job opportunities.
"""
import os
import uuid
from django.db import models

def resume_file_path(instance, filename):
    """Generate file path for the volunteer application resume while still maintaining original file ext."""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f'{uuid.uuid4()}{ext}' # create a unique filename using uuid

    return os.path.join('volunteer_applications','resume',f'user_{instance.pathfinder.user_id}', filename)

def cover_letter_file_path(instance, filename):
    """Generate file path for the volunteer application cover letter while still maintaining original file ext."""
    ext = os.path.splitext(filename)[1]  # Get the file extension
    filename = f'{uuid.uuid4()}{ext}' # create a unique filename using uuid

    return os.path.join('volunteer_applications','cover_letter',f'user_{instance.pathfinder.user_id}', filename)

class VolunteerPosting(models.Model):
    """this is the model that shows everything about the Volunteer postings."""
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        DRAFT = "draft", "Draft"

    class JobType(models.TextChoices):
        ONSITE = "onsite", "Onsite"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    class EngagementType(models.TextChoices):
        VOLUNTEER = "volunteer", "Volunteer"

    title = models.CharField(max_length=100, blank=False, null=False)
    description  = models.TextField(blank=False, null=False)
    status = models.CharField(max_length=10, choices=Status.choices, blank=False, null=False)
    location = models.CharField(max_length=200, blank=False, null=False)
    enabler = models.ForeignKey("profiles.EnablerProfile", on_delete=models.CASCADE, related_name="volunteer_postings", blank=False, null=False)
    job_type = models.CharField(max_length=10,choices=JobType.choices, blank=False, null=False)
    engagement_type = models.CharField(max_length=12,choices=EngagementType.choices, default= EngagementType.VOLUNTEER,blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    application_deadline = models.DateTimeField(blank=True, null=True) # some applications may always be open
    stipend = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    contact_email = models.EmailField(max_length=254, blank=False, null=False)
    contact_phone = models.CharField(max_length=20, blank=False, null=False)

    def __str__(self):
        return f"{self.id} - {self.title}"


class VolunteerApplication(models.Model):
    """this model would hold the volunteer applications."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    volunteer_posting = models.ForeignKey("VolunteerPosting", on_delete=models.CASCADE, related_name="applications", blank=False, null=False)
    pathfinder = models.ForeignKey("profiles.PathfinderProfile", on_delete=models.CASCADE, related_name="volunteer_applications", blank=False, null=False)
    cover_letter = models.FileField(upload_to=cover_letter_file_path,blank=True, null=True)
    resume = models.FileField(upload_to=resume_file_path, blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=Status.choices, blank=False, null=False, default=Status.PENDING)  # e.g., pending, accepted, rejected

    def __str__(self):
        return f"{self.id} - {self.pathfinder.user.email} - {self.volunteer_posting.title}"

# class VolunteerApplicationStatusHistory(models.Model):
#     """this model would hold the history of status changes for volunteer applications."""
#     volunteer_application = models.ForeignKey("VolunteerApplication", on_delete=models.CASCADE, related_name="status_history", blank=False, null=False)
#     previous_status = models.CharField(max_length=50, blank=False, null=False)
#     new_status = models.CharField(max_length=50, blank=False, null=False)
#     changed_at = models.DateTimeField(auto_now_add=True)
#     changed_by = models.ForeignKey("profiles.EnablerProfile", on_delete=models.SET_NULL, related_name="changed_volunteer_application_statuses", blank=True, null=True)

class VolunteerApplicationNote(models.Model):
    """this model would hold notes added to volunteer applications. These notes can be added by enablers reviewing the applications."""
    volunteer_application = models.ForeignKey("VolunteerApplication", on_delete=models.CASCADE, related_name="notes", blank=False, null=False)
    note = models.TextField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("profiles.EnablerProfile", on_delete=models.CASCADE, related_name="created_volunteer_application_notes", blank=False, null=False)

    def __str__(self):
        return f"{self.id} - {self.volunteer_application.pathfinder.user.email} - Note by {self.created_by.user.email}"