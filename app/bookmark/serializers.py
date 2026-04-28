from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Bookmark, BookmarkUser, BookmarkEnabler
from opportunities.models import Opportunity
from opportunities.serializers import OpportunitySerializer
from profiles.serializers import ApplicantProfileSerializer, OrganizationProfileSerializer
from profiles.models import PathfinderProfileExtra, EnablerProfileExtra

from django.contrib.auth import get_user_model

User = get_user_model()

# write serializers here
class BookmarkUserSerializer(serializers.ModelSerializer):
    # Write-only: the enabler submits the pathfinder's Django user ID (what the frontend has).
    # The validate() method resolves this to a PathfinderProfileExtra instance (what the model stores).
    pathfinder_id = serializers.IntegerField(write_only=True)

    # Read-only: included in list responses so the frontend can build the DELETE URL
    # (/api/bookmark/applicants/saved/<pathfinder_user_id>/) without a separate lookup.
    pathfinder_user_id = serializers.IntegerField(source='pathfinder.profile.user.id', read_only=True)

    pathfinder_details = ApplicantProfileSerializer(
        source='pathfinder',
        read_only=True
    )

    class Meta:
        model = BookmarkUser
        fields = ['id', 'pathfinder_id', 'pathfinder_user_id', 'pathfinder_details', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        enabler = self.context['request'].user
        # Pop pathfinder_id (write-only) and resolve it to the profile object before saving.
        pathfinder_user_id = attrs.pop('pathfinder_id')

        try:
            pathfinder = PathfinderProfileExtra.objects.select_related('profile__user').get(
                profile__user__id=pathfinder_user_id
            )
        except PathfinderProfileExtra.DoesNotExist:
            raise serializers.ValidationError("No pathfinder profile found for this user.")

        if pathfinder.profile.user.role != 'pathfinder':
            raise serializers.ValidationError("You can only bookmark pathfinder profiles.")

        if BookmarkUser.objects.filter(enabler=enabler, pathfinder=pathfinder).exists():
            raise serializers.ValidationError("You have already bookmarked this pathfinder.")

        attrs['pathfinder'] = pathfinder
        return attrs


class BookmarkSerializer(serializers.ModelSerializer):
    opportunity = OpportunitySerializer(read_only=True)
    opportunity_id = serializers.PrimaryKeyRelatedField(
        queryset=Opportunity.objects.all(),
        source='opportunity',
        write_only=True
    )

    class Meta:
        model = Bookmark
        fields = ['id', 'opportunity', 'opportunity_id', 'created_at']
        read_only_fields = ['created_at']
        

    def validate(self, attrs):
        user = self.context['request'].user
        opportunity = attrs.get('opportunity')

        if not opportunity.is_open:
            raise serializers.ValidationError("You cannot bookmark a closed opportunity.")

        # Enforce unique together here since the user comes from request, not payload
        if Bookmark.objects.filter(user=user, opportunity=opportunity).exists():
            raise serializers.ValidationError("You have already bookmarked this opportunity.")
        return attrs

class BookmarkEnablerSerializer(serializers.ModelSerializer):
    # Same write-only / read-only pattern as BookmarkUserSerializer:
    # enabler_id is accepted on write (Django user ID), enabler_user_id is returned on read.
    enabler_id = serializers.IntegerField(write_only=True)
    enabler_user_id = serializers.IntegerField(source='enabler.profile.user.id', read_only=True)
    enabler_details = OrganizationProfileSerializer(
        source='enabler',
        read_only=True
    )

    class Meta:
        model = BookmarkEnabler
        fields = ['id', 'enabler_id', 'enabler_user_id', 'enabler_details', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        pathfinder = self.context['request'].user
        enabler_user_id = attrs.pop('enabler_id')

        try:
            enabler = EnablerProfileExtra.objects.select_related('profile__user').get(
                profile__user__id=enabler_user_id
            )
        except EnablerProfileExtra.DoesNotExist:
            raise serializers.ValidationError("No enabler profile found for this user.")

        if enabler.profile.user.role != 'enabler':
            raise serializers.ValidationError("You can only bookmark enabler profiles.")

        if BookmarkEnabler.objects.filter(pathfinder=pathfinder, enabler=enabler).exists():
            raise serializers.ValidationError("You have already bookmarked this enabler.")

        attrs['enabler'] = enabler
        return attrs