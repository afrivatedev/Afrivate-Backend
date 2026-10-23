from rest_framework import serializers

from .models import ExternalOpportunity


class ExternalOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOpportunity
        fields = [
            'id', 'source', 'title', 'organization_name', 'description',
            'apply_url', 'source_url', 'field', 'opportunity_type', 'location', 'is_remote',
            'deadline', 'posted_at',
        ]
        read_only_fields = fields
