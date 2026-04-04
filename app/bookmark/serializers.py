from rest_framework import serializers

from .models import Bookmark, BookmarkUser
from opportunities.models import Opportunity
from opportunities.serializers import OpportunitySerializer
from profiles.serializers import ApplicantProfileSerializer
from profiles.models import PathfinderProfileExtra

from django.contrib.auth import get_user_model

User = get_user_model()

# write serializers here
class BookmarkUserSerializer(serializers.ModelSerializer):
    # Write: accept a pathfinder's profile extra pk to bookmark them

    pathfinder_id = serializers.PrimaryKeyRelatedField(
        queryset=PathfinderProfileExtra.objects.all(),  
        # queryset=User.objects.filter(profile__pathfinder_extra__isnull=False),
        source='pathfinder',
        write_only=True
    )
    # Read: return the pathfinder's profile details 
    pathfinder_details = ApplicantProfileSerializer(
        source='pathfinder',
        read_only=True
    )

    class Meta:
        model = BookmarkUser
        fields = ['id', 'pathfinder_id', 'pathfinder_details', 'created_at']
        read_only_fields = ['created_at']


    def validate(self, attrs):
        enabler = self.context['request'].user
        pathfinder = attrs.get('pathfinder')

        # Enforce unique together here since the enabler comes from request, not payload
        if BookmarkUser.objects.filter(enabler=enabler, pathfinder=pathfinder).exists():
            raise serializers.ValidationError("You have already bookmarked this pathfinder.")
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

        # Enforce unique together here since the user comes from request, not payload
        if Bookmark.objects.filter(user=user, opportunity=opportunity).exists():
            raise serializers.ValidationError("You have already bookmarked this opportunity.")
        return attrs
