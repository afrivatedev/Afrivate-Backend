"""
Serializer for the profile endpoint.
"""

from rest_framework import serializers
from django.conf import settings
from PIL import Image

from profiles.models import (
    EnablerProfile,
    PathfinderProfile,
    EnablerCredential,
    EnablerSocialLink,
    PathfinderSocialLink,
    Education,
    WorkExperience,
    Certification,
    Skill,
    Language,
)


class EnablerProfileSerializer(serializers.ModelSerializer):
    """serializer for the enabler profile."""

    class Meta:
        model = EnablerProfile
        exclude = ("user", "profile_pic")
        read_only_fields = ("id","created_at", "updated_at")


class PathfinderProfileSerializer(serializers.ModelSerializer):
    """Serializer for the Pathfinder Profile"""

    # Make M2M optional so clients can create profile without providing them
    skills = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Skill.objects.all(), required=False
    )
    languages = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Language.objects.all(), required=False
    )

    class Meta:
        model = PathfinderProfile
        exclude = ("user", "profile_pic")
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        """Handle M2M relationships on create."""
        skills = validated_data.pop("skills", [])
        languages = validated_data.pop("languages", [])
        profile = PathfinderProfile.objects.create(**validated_data)
        profile.skills.set(skills)
        profile.languages.set(languages)
        return profile


class ProfilePictureSerializer(serializers.Serializer):
    """serializer for enabler profile picture update and retrieve"""

    profile_pic = serializers.ImageField(allow_empty_file=False)

    def validate_profile_pic(self, file):
        """Validate image type and size using Pillow and configured limits."""
        # Size check
        max_mb = getattr(settings, "MAX_PROFILE_PIC_MB", 5)  # default 5MB
        max_bytes = max_mb * 1024 * 1024
        size = getattr(file, "size", None)
        if size is not None and size > max_bytes:
            raise serializers.ValidationError(
                f"Image too large. Max size is {max_mb} MB."
            )

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

        allowed = getattr(
            settings, "PROFILE_PIC_ALLOWED_FORMATS", {"JPEG", "JPG", "PNG", "WEBP"}
        )
        fmt = getattr(img, "format", None) if img else None
        if fmt:
            if (
                fmt.upper() == "JPG"
            ):  # this is a quirk with pillow, where it returns JPG even if the format is JPEG
                fmt = "JPEG"
            if allowed and fmt.upper() not in {a.upper() for a in allowed}:
                allowed_str = ", ".join(sorted(allowed))
                raise serializers.ValidationError(
                    f"Unsupported image format: {fmt}. Allowed: {allowed_str}."
                )

        return file

    def update(self, instance, validated_data):
        """Replace profile picture and delete the old file from storage safely."""
        new_file = validated_data.get("profile_pic")
        old_name = (
            instance.profile_pic.name
            if getattr(instance, "profile_pic", None)
            else None
        )

        # Perform the default update (assigns and saves the new file)
        instance.profile_pic = new_file
        instance.save()

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


class EnablerCredentialSerializer(serializers.ModelSerializer):
    """serializer for the enabler credential model."""

    class Meta:
        model = EnablerCredential
        exclude = ("profile",)
        read_only_fields = ("id", "created_at", "updated_at")


class CertificationSerializer(serializers.ModelSerializer):
    """serializer for the certification model."""
    class Meta:
        model = Certification
        exclude = ("profile",)
        read_only_fields = ("id","is_verified", "created_at", "updated_at")


class EnablerSocialLinkSerializer(serializers.ModelSerializer):
    """serializer for social links for both enabler"""

    class Meta:
        model = EnablerSocialLink
        exclude = ("profile",)
        read_only_fields = ("id","created_at", "updated_at")


class PathfinderSocialLinkSerializer(serializers.ModelSerializer):
    """serializer for social links for pathfinder profiles."""

    class Meta:
        model = PathfinderSocialLink  #
        exclude = ("profile",)
        read_only_fields = ("id", "created_at", "updated_at")
