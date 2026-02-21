from rest_framework import serializers
from .models import Application

class ApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    opportunity_title = serializers.ReadOnlyField(source='opportunity.title')
    
    class Meta:
        model = Application
        fields = ['id','user','user_name','opportunity','opportunity_title', 'status', 'cover_letter', 'applied_at', 'reviewed_at']
        read_only_fields = ['status', 'user', 'applied_at', 'reviewed_at']

    def validate_opportunity(self, value):
        # Prevent double applications logic is handled by Meta unique_together, 
        if not value.is_open:
            raise serializers.ValidationError("This Opportunity is no longer available.")
        return value
    
# i want to create a "Profile Snapshot" or a nested serializer so the Enabler can view the pathfinder resume at once