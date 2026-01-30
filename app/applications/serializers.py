from rest_framework import serializers
from .models import Application

class ApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    opportunity_title = serializers.ReadOnlyField(source='opportunity.title')
    
    class Meta:
        model = Application
        fields = ['user','user_name','opportunity','opportunity_title', 'status', 'applied_at', 'reviewed_at']
        read_only_fields = ['status', 'user', 'applied_at', 'reviewed_at']

    def validate(self, data):
        # Prevent double applications logic is handled by Meta unique_together, 
        return data