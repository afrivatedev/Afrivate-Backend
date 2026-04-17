from rest_framework import serializers
from .models import Opportunity
from django.utils import timezone
from datetime import timedelta

# write serializers here
class OpportunitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        try:
            return obj.created_by.profile.enabler_extra.name
        except Exception:
            return obj.created_by.username
        
        
    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'opportunity_type', 'description', 
            'link', 'posted_at', 'is_open', 'created_by_name', 'created_by'
        ]
        
        read_only_fields = ['created_by', 'posted_at']

    def validate_link(self, value):
        """Ensure the link is a valid secure URL."""
        if not value.startswith('https://'):
            raise serializers.ValidationError("For security, all opportunity links must use HTTPS.")
        return value

    def validate(self, data):
        """Enforce the Limited Edit Window (e.g., 12 hours)."""
        # Check if this is an update request (instance exists)
        if self.instance:
            edit_limit = self.instance.posted_at + timedelta(hours=12)
            if timezone.now() > edit_limit:
                raise serializers.ValidationError(
                    "The edit window for this opportunity has closed (12h limit)."
                )
        return data
