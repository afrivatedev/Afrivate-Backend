from rest_framework import serializers
from .models import Opportunity, Bookmark

class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ['id', 'title', 'description', 'link', 'posted_at', 'is_open']


class BookmarkSerializer(serializers.ModelSerializer):
    opportunity = OpportunitySerializer(read_only=True)  # nested details
    opportunity_id = serializers.PrimaryKeyRelatedField(
        queryset=Opportunity.objects.all(),
        source='opportunity',
        write_only=True
    )

    class Meta:
        model = Bookmark
        fields = ['id', 'opportunity', 'opportunity_id', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate(self, data):
        user = self.context['request'].user
        opportunity = data['opportunity']
        if Bookmark.objects.filter(user=user, opportunity=opportunity).exists():
            raise serializers.ValidationError("You already bookmarked this opportunity.")
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)