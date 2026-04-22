from rest_framework import serializers
from .models import Application
from profiles.serializers import PathfinderProfileSerializer, SignedCloudinaryFileField
from profiles.models import PathfinderProfileExtra

class ApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    opportunity_title = serializers.ReadOnlyField(source='opportunity.title')
    pathfinder_profile = serializers.SerializerMethodField()
    resume = SignedCloudinaryFileField(required=False, allow_null=True)
    profile_resume_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = ['id','user','user_name','pathfinder_profile',
                'opportunity','opportunity_title', 'resume', 'profile_resume', 'profile_resume_url', 'status',
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
            extra = PathfinderProfileExtra.objects.select_related('profile__user').prefetch_related(   # prefetch related to optimize queries 
                'profile__social_links', 'profile__credentials',
                'pathfinder_skills', 'pathfinder_education',
                'pathfinder_certifications'
            ).get(profile__user=obj.user)
            
            return PathfinderProfileSerializer(extra, context=self.context).data
        except PathfinderProfileExtra.DoesNotExist:
            return None

    def validate(self, data):
        user = self.context['request'].user
        # 🚨 Safety Check: Only Pathfinders can apply
        if user.role != 'pathfinder':
            raise serializers.ValidationError("Only Pathfinders can apply for opportunities.")
        return data
    
    def get_profile_resume_url(self, obj):
        try:
            if obj.profile_resume and obj.profile_resume.document:
                return obj.profile_resume.document.url
        except Exception as e:
            print(f"Resume URL error: {e}")
            return None
        return None
    
class ApplicationListSerializer(serializers.ModelSerializer):
    applicant_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    resume = SignedCloudinaryFileField(read_only=True)

    pathfinder_profile_id = serializers.SerializerMethodField() 
    profile_resume_url = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'applicant_id', 'username', 'email',
            'status', 'cover_letter', 'applied_at', 'resume',
            'pathfinder_profile_id', 'profile_resume_url'
        ]
        read_only_fields = fields

    def get_pathfinder_profile_id(self, obj):
        try:
            return obj.user.profile.pathfinder_extra.id
        except Exception:
            return None
        
    def get_profile_resume_url(self, obj):
        """Returns the signed URL of the credential used as resume"""
        try:
            if obj.profile_resume and obj.profile_resume.document:
                import cloudinary.utils
                url, _ = cloudinary.utils.cloudinary_url(
                    obj.profile_resume.document.name,
                    resource_type="raw",
                    type="upload",
                    sign_url=True,
                    secure=True
                )
                return url
        except Exception:
            return None
        return None