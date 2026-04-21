"""
Serializer for the profile endpoint.
"""
import os

from rest_framework import serializers
from django.conf import settings
from PIL import Image
from django.core.exceptions import ValidationError
from django.db import transaction

import cloudinary.utils

from django.db import models
from profiles.models import (
    Profile,
    SocialLink,
    Credential,
    EnablerProfileExtra,
    PathfinderProfileExtra,
    PathfinderSkill,
    PathfinderEducation,
    PathfinderCertification,
)
import logging

logger = logging.getLogger(__name__)

class SignedCloudinaryFileField(serializers.FileField):
    """
    A read-aware serializer field that generates a signed Cloudinary URL when
    serializing file/document fields.
    """

    def to_representation(self, value):
        if not value or not hasattr(value, 'name') or not value.name:
            return None
            
        try:
            url, _ = cloudinary.utils.cloudinary_url(
                value.name,
                resource_type="raw", 
                type="upload",      
                sign_url=True,
                secure=True,
            )
            return url
        except Exception as e:  
            logger.error(f"Cloudinary Signature Error: {e}")
            return value.url

class SocialLinkSerializer(serializers.ModelSerializer):
    """serializer for the social link model"""
    class Meta:
        model = SocialLink
        fields = ("id", "platform_name", "platform_url")
        read_only_fields = ("id",)

class CredentialSerializer(serializers.ModelSerializer):
    """serializer for the credential model"""
    document = SignedCloudinaryFileField(required=True)
    # Not required from the client — falls back to the uploaded file's original name
    document_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = Credential
        fields = ("id", "document_name", "document", "is_verified")
        read_only_fields = ("id", "is_verified")

    def _resolve_document_name(self, validated_data):
        """
        Ensure document_name is always meaningful.
        If the client omits it or sends a blank/generic value, derive it from
        the uploaded file's original filename (available on the InMemoryUploadedFile
        object before storage renames it to a UUID path).
        """
        name = validated_data.get('document_name', '').strip()
        if not name:
            document = validated_data.get('document')
            if document and hasattr(document, 'name'):
                name = os.path.splitext(os.path.basename(document.name))[0]
            validated_data['document_name'] = name or 'document'
        return validated_data

    def create(self, validated_data):
        validated_data = self._resolve_document_name(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._resolve_document_name(validated_data)
        return super().update(instance, validated_data)

class ProfileSerializer(serializers.ModelSerializer):
    """serializer for the enabler profile extra fields"""
    class Meta:
        model = Profile
        exclude = ("user",)
        read_only_fields = ("id","profile_pic", "created_at")

class SkillSerializer(serializers.ModelSerializer):
    """serializer for the pathfinder skill model"""
    class Meta:
        model = PathfinderSkill
        fields = ("name",)

class EducationSerializer(serializers.ModelSerializer):
    """serializer for the pathfinder education model"""
    class Meta:
        model = PathfinderEducation
        fields = ("name",)

class CertificationSerializer(serializers.ModelSerializer):
    """serializer for the pathfinder certification model"""
    class Meta:
        model = PathfinderCertification
        fields = ("name",)

class BaseProfileSerializer(serializers.ModelSerializer):
    base_details = ProfileSerializer(source="profile", many=False, read_only=False, required=True)
    social_links = SocialLinkSerializer(many=True, required=False)
    # since social_links is actually not a direct field under the EnablerProfileExtra serializer, then we have to manage
    # its inclusion in the response manually.
    
    def _get_or_create_social_links(self, social_links_data, profile, replace=False):
        """Create social links from nested data; optionally replace existing ones."""
        if replace:
            profile.social_links.all().delete()
        for links in (social_links_data or []):
            SocialLink.objects.get_or_create(
                profile=profile,
                platform_name=links.get("platform_name"),
                platform_url=links.get("platform_url"),
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        base_details_data = validated_data.pop("profile", None)
        social_links_data = validated_data.pop("social_links", None)
        logger.debug(f"Updating profile for {instance.profile.user.username}. Base details: {base_details_data}, Social links: {social_links_data}")

        if base_details_data:
            profile_instance = instance.profile

            for attr, value in base_details_data.items():
                setattr(profile_instance, attr, value)
            profile_instance.save()

        # If social_links provided, replace existing with new set
        if social_links_data is not None:
            logger.debug(f"Updating social links for {instance.profile.user.username}. Data: {social_links_data}")
            self._get_or_create_social_links(social_links_data, instance.profile, replace=True)

        for attr, value in validated_data.items():
            if not isinstance(value, (list, models.QuerySet)):
                setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        """Ensure social_links are serialized from the related Profile."""
        data = super().to_representation(instance)
        # Serialize social links from the profile relation so it's always present in responses
        links_qs = instance.profile.social_links.all()
        data["social_links"] = SocialLinkSerializer(links_qs, many=True).data
        return data


class EnablerProfileSerializer(BaseProfileSerializer):
    """writes into the fields of the profile model and adds extra fields for the enabler profile"""

    class Meta:
        model = EnablerProfileExtra
        exclude = ("profile",)
        read_only_fields = ("id",)


    def validate(self, attrs):
        user = self.context["request"].user
        if user.role != "enabler":
            raise serializers.ValidationError("Only users with Enabler role can access Enabler profiles.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        base_details_data = validated_data.pop("profile", None)  # 'profile' key comes from source on base_details
        social_links_data = validated_data.pop("social_links", [])
        logger.debug(f"Creating Enabler profile for {user.username}. Base details: {base_details_data}, Social links: {social_links_data}")

        if base_details_data is None:
            raise serializers.ValidationError("Profile data is required to create Enabler profile.")
        # profile = Profile.objects.create(user=user, **base_details_data)
        profile, _ = Profile.objects.update_or_create(user=user, defaults=base_details_data)
        enabler_extra, _ = EnablerProfileExtra.objects.update_or_create(profile=profile, defaults=validated_data)
        self._get_or_create_social_links(social_links_data, profile, replace=False)
        return enabler_extra

    def clean(self):
        if self.profile.user.role != 'enabler':
            raise ValidationError("User role must be 'enabler' to have this profile type.")


class PathfinderProfileSerializer(BaseProfileSerializer):
    skills = SkillSerializer(source="pathfinder_skills", many=True, required=False)
    educations = EducationSerializer(source="pathfinder_education", many=True, required=False)
    certifications = CertificationSerializer(source="pathfinder_certifications", many=True, required=False)
    credentials = CredentialSerializer(source="profile.credentials", many=True, read_only=True)  # ← add this

    class Meta:
        model = PathfinderProfileExtra
        exclude = ("profile",)
        read_only_fields = ("id",)

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role != "pathfinder":
            raise serializers.ValidationError("Only users with Pathfinder role can access Pathfinder profiles.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        base_details_data = validated_data.pop("profile", None)
        social_links_data = validated_data.pop("social_links", None)
        skills_data = validated_data.pop("pathfinder_skills", [])
        educations_data = validated_data.pop("pathfinder_education", [])
        certifications_data = validated_data.pop("pathfinder_certifications", [])

        if base_details_data is None:
            raise serializers.ValidationError("Profile data is required to create Pathfinder profile.")
        
        # profile = Profile.objects.create(user=user, **base_details_data)
        profile, _ = Profile.objects.update_or_create(user=user, defaults=base_details_data)
        # pathfinder_extra, _ = PathfinderProfileExtra.objects.update_or_create(profile=profile, **validated_data)
        # pathfinder_extra = PathfinderProfileExtra.objects.create(profile=profile, **validated_data)
        pathfinder_extra, _ = PathfinderProfileExtra.objects.update_or_create(profile=profile, defaults=validated_data) 
        self._get_or_create_social_links(social_links_data, profile, replace=False)

        if skills_data:
            PathfinderSkill.objects.bulk_create([PathfinderSkill(pathfinder=pathfinder_extra, **skill) for skill in skills_data])
            
        if educations_data:
            PathfinderEducation.objects.bulk_create([PathfinderEducation(pathfinder=pathfinder_extra, **edu) for edu in educations_data])
            
        if certifications_data:
            PathfinderCertification.objects.bulk_create([PathfinderCertification(pathfinder=pathfinder_extra, **cert) for cert in certifications_data])
            
        return pathfinder_extra

    def update(self, instance, validated_data):
        skills_data = validated_data.pop("pathfinder_skills", None)
        educations_data = validated_data.pop("pathfinder_education", None)
        certifications_data = validated_data.pop("pathfinder_certifications", None)

        instance = super().update(instance, validated_data)

        if skills_data is not None:
            instance.pathfinder_skills.all().delete()
            PathfinderSkill.objects.bulk_create([
                PathfinderSkill(pathfinder=instance, **skill) for skill in skills_data
            ])

        if educations_data is not None:
            instance.pathfinder_education.all().delete()
            PathfinderEducation.objects.bulk_create([
                PathfinderEducation(pathfinder=instance, **edu) for edu in educations_data
            ])

        if certifications_data is not None:
            instance.pathfinder_certifications.all().delete()
            PathfinderCertification.objects.bulk_create([
                PathfinderCertification(pathfinder=instance, **cert) for cert in certifications_data
            ])

        return instance

    def clean(self):
        if self.profile.user.role != 'pathfinder':
            raise ValidationError("User role must be 'pathfinder' to have this profile type.")
    
class ProfilePictureSerializer(serializers.ModelSerializer):
    """serializer for enabler profile picture update and retrieve"""
    class Meta:
        model = Profile
        fields = ("id","profile_pic",)
        read_only_fields = ("id",)
        extra_kwargs = {"profile_pic": {"required": True}}

    def validate_profile_pic(self, file):
        """Validate image type and size using Pillow and configured limits."""
        # Size check
        max_mb = getattr(settings, "MAX_PROFILE_PIC_MB", 5)  # default 5MB
        max_bytes = max_mb * 1024 * 1024
        size = getattr(file, "size", None)
        if size is not None and size > max_bytes:
            raise serializers.ValidationError(f"Image too large. Max size is {max_mb} MB.")

        # Type/format check with Pillow
        img = None
        try:
            img = Image.open(file)
            img.verify()  # verify file is a valid image
        except (Image.UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise serializers.ValidationError("Upload a valid image file.")
        finally:
            if hasattr(file, "seek"):
                try:
                    file.seek(0)
                except Exception:
                    pass

        allowed = getattr(settings, "PROFILE_PIC_ALLOWED_FORMATS", {"JPEG", "JPG", "PNG", "WEBP"})
        fmt = getattr(img, "format", None) if img else None
        if fmt:
            if fmt.upper() == "JPG": # this is a quirk with pillow, where it returns JPG even if the format is JPEG
                fmt = "JPEG"
            if allowed and fmt.upper() not in {a.upper() for a in allowed}:
                allowed_str = ", ".join(sorted(allowed))
                raise serializers.ValidationError(f"Unsupported image format: {fmt}. Allowed: {allowed_str}.")

        return file

    def update(self, instance, validated_data):
        """Replace profile picture and delete the old file from storage safely."""
        new_file = validated_data.get("profile_pic")
        old_name = instance.profile_pic.name if getattr(instance, "profile_pic", None) else None

        # Perform the default update (assigns and saves the new file)
        instance = super().update(instance, validated_data)

        # Clean up old file if different
        if new_file and old_name and old_name != instance.profile_pic.name:
            try:
                storage = instance.profile_pic.storage
                if storage.exists(old_name):
                    storage.delete(old_name)
            except Exception:
                # Swallow storage errors to avoid failing the request due to cleanup issues
                pass

        return instance

class ApplicantProfileSerializer(serializers.ModelSerializer):
    """for enablers viewing a pathfinder applicant's profile"""
    base_details = ProfileSerializer(source="profile", read_only=True)
    skills = SkillSerializer(source="pathfinder_skills", many=True, read_only=True)
    educations = EducationSerializer(source="pathfinder_education", many=True, read_only=True)
    certifications = CertificationSerializer(source="pathfinder_certifications", many=True, read_only=True)
    social_links = SocialLinkSerializer(source="profile.social_links", many=True, read_only=True)
    credentials = CredentialSerializer(source="profile.credentials", many=True, read_only=True)

    class Meta:
        model = PathfinderProfileExtra
        fields = [
            'id', 'first_name', 'last_name', 'other_name', 'title',
            'about', 'work_experience', 'languages',
            'base_details', 'social_links', 'credentials',
            'skills', 'educations', 'certifications'
        ]

class OrganizationProfileSerializer(serializers.ModelSerializer):
    """for pathfinders viewing an Organization's profile"""
    base_details = ProfileSerializer(source="profile", read_only=True)
    social_links = SocialLinkSerializer(source="profile.social_links", many=True, read_only=True)

    class Meta:
        model = EnablerProfileExtra
        fields = [
            'id',
            'name',
            'employees',
            'role',
            'base_details',
            'social_links'
        ]
