from rest_framework import serializers
from .models import Application
from profiles.serializers import PathfinderProfileSerializer

class ApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    opportunity_title = serializers.ReadOnlyField(source='opportunity.title')
    pathfinder_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = ['id','user','user_name','pathfinder_profile',
                  'opportunity','opportunity_title', 'status',
                    'cover_letter', 'applied_at', 'reviewed_at', ]
        read_only_fields = ['status', 'user', 'applied_at', 'reviewed_at']

    def validate_opportunity(self, value):
        # Prevent double applications logic is handled by Meta unique_together, 
        if not value.is_open:
            raise serializers.ValidationError("This Opportunity is no longer available.")
        return value
    
    # i want to create a "Profile Snapshot" or a nested serializer so the Enabler can view the pathfinder resume at once

    def get_pathfinder_profile(self, obj):
        # Fetch the PathfinderExtra related to the user who applied
        try:
            from profiles.models import PathfinderProfileExtra
            extra = PathfinderProfileExtra.objects.get(profile__user=obj.user)
            return PathfinderProfileSerializer(extra).data
        except:
            return None

    def validate(self, data):
        user = self.context['request'].user
        # 🚨 Safety Check: Only Pathfinders can apply
        if user.role != 'pathfinder':
            raise serializers.ValidationError("Only Pathfinders can apply for opportunities.")
        return data