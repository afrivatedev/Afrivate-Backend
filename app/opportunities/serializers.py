from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
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
        # UniqueTogetherValidator catches (title, link) duplicates and returns a clean 400.
        # The model also has unique_together which would raise an IntegrityError without this.
        validators = [
            UniqueTogetherValidator(
                queryset=Opportunity.objects.all(),
                fields=['title', 'link'],
                message="An opportunity with this title and link already exists.",
            )
        ]

    def validate_link(self, value):
        # Enforce HTTPS — plain HTTP links would expose applicants to MITM redirects.
        if not value.startswith('https://'):
            raise serializers.ValidationError("For security, all opportunity links must use HTTPS.")
        return value

    def validate(self, data):
        # Edit window check runs only on updates (self.instance is set). This is the
        # serializer-level guard; the model's can_edit() method provides the same logic
        # for programmatic use outside the API.
        if self.instance:
            edit_limit = self.instance.posted_at + timedelta(hours=12)
            if timezone.now() > edit_limit:
                raise serializers.ValidationError(
                    "The edit window for this opportunity has closed (12h limit)."
                )
        return data
