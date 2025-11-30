"""
Serializer for the profile endpoint.
"""
from rest_framework import serializers

from profiles.models import (
    PathfinderProfile, EnablerProfile, Credential, SocialLink)

class SocialLinkSerializer(serializers.ModelSerializer):
    """serializer for the social link model"""
    class Meta:
        model = SocialLink
        fields = ("id", "platform_name", "platform_url")
        read_only_fields = ("id",)

class CredentialSerializer(serializers.ModelSerializer):
    """serializer for the credential model"""
    class Meta:
        model = Credential
        fields = ("id", "document_name", "document")
        read_only_fields = ("id",)

class PathfinderProfileSerializer(serializers.ModelSerializer):
    """Making it possible to create social links as part of the profile, any update to the social links
    should be done via the social links endpoint."""

    """serializer for the profile model"""
    social_links = SocialLinkSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = PathfinderProfile  # or EnablerProfile based on your use case
        exclude = ("user")
        read_only_fields = ("id","profile_pic")

    def _get_or_create_social_links(self, social_links_data, profile):
        """Helper method to get or create social links from the nested data"""
        auth_user = self.context["request"].user

        for links in social_links_data:
            link_obj, created = SocialLink.objects.get_or_create(
                pathfinder_profile= auth_user.pathfinderprofile,
                **links
            )
            profile.social_links.add(link_obj)

    def create(self, validated_data):
        social_links_data = validated_data.pop('social_links', [])
        profile = PathfinderProfile.objects.create(**validated_data)
        self._get_or_create_social_links(social_links_data, profile)

        return profile

    def update(self, instance, validated_data):
        """deletes any social link sent as an update, to update social link, use social link end-point."""
        del validated_data['social_links']
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class EnablerProfileSerializer(serializers.ModelSerializer):
    """Making it possible to create social links as part of the profile, any update to the social links
        should be done via the social links endpoint."""
    social_links = SocialLinkSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = EnablerProfile
        exclude = ("user",)
        read_only_fields = ("id","profile_pic")

    def _get_or_create_social_links(self, social_links_data, profile):
        """Helper method to get or create social links from the nested data"""
        auth_user = self.context["request"].user

        for links in social_links_data:
            link_obj, created = SocialLink.objects.get_or_create(
                enabler_profile= auth_user.enablerprofile,
                **links
            )
            profile.social_links.add(link_obj)

    def create(self, validated_data):
        social_links_data = validated_data.pop('social_links', [])
        profile = EnablerProfile.objects.create(**validated_data)
        self._get_or_create_social_links(social_links_data, profile)

        return profile

    def update(self, instance, validated_data):
        """deletes any social link sent as an update, to update social link, use social link end-point."""
        del validated_data['social_links']
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class PathfinderProfilePicSerializer(serializers.ModelSerializer):
    """serializer for pathfinder profile picture update and retrieve"""

    class Meta:
        model = PathfinderProfile
        fields = ("id","profile_pic",)
        read_only_fields = ("id",)
    extra_kwargs = {"profile_pic": {"required": True}}

class EnablerProfilePicSerializer(serializers.ModelSerializer):
    """serializer for enabler profile picture update and retrieve"""

    class Meta:
        model = EnablerProfile
        fields = ("id","profile_pic",)
        read_only_fields = ("id",)
    extra_kwargs = {"profile_pic": {"required": True}}