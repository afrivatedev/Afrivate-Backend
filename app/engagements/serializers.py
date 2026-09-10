from rest_framework import serializers
from .models import EngagementRecord, TaskEntry, Certificate

class TaskEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskEntry
        fields = ['id', 'date', 'description', 'logged_by', 'created_at']
        read_only_fields = ['id', 'logged_by', 'created_at']

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'skill_summary_text', 'pdf_file', 'verification_page_url', 'issued_at', 'last_updated_at', 'revoked']
        read_only_fields = ['id', 'pdf_file', 'verification_page_url', 'issued_at', 'last_updated_at', 'revoked']

class EngagementRecordSerializer(serializers.ModelSerializer):
    tasks = TaskEntrySerializer(many=True, read_only=True)
    certificate = CertificateSerializer(read_only=True)
    volunteer_name = serializers.CharField(source='volunteer.username', read_only=True)
    organization_name = serializers.CharField(source='organization.username', read_only=True)
    attested_by_name = serializers.CharField(source='attested_by_user.username', read_only=True, allow_null=True)

    class Meta:
        model = EngagementRecord
        fields = [
            'id', 'volunteer', 'volunteer_name', 'organization', 'organization_name',
            'opportunity', 'role_title', 'role_skill_tags', 'start_date', 'end_date',
            'total_hours', 'status', 'attested_by_user', 'attested_by_name', 'attested_at',
            'attestation_notes', 'dispute_reason', 'created_at', 'updated_at', 'tasks', 'certificate'
        ]
        read_only_fields = [
            'id', 'volunteer', 'volunteer_name', 'organization', 'organization_name',
            'opportunity', 'role_title', 'role_skill_tags', 'start_date', 'status',
            'attested_by_user', 'attested_by_name', 'attested_at', 'created_at', 'updated_at'
        ]

class PublicCertificateSerializer(serializers.ModelSerializer):
    """
    Used for the unauthenticated verification page.
    Only exposes safe fields.
    """
    volunteer_name = serializers.CharField(source='engagement_record.volunteer.username')
    # Can change to full name if using PathfinderProfileExtra
    organization_name = serializers.CharField(source='engagement_record.organization.username')
    # Can change to name from EnablerProfileExtra
    role_title = serializers.CharField(source='engagement_record.role_title')
    start_date = serializers.DateField(source='engagement_record.start_date')
    end_date = serializers.DateField(source='engagement_record.end_date')
    total_hours = serializers.DecimalField(source='engagement_record.total_hours', max_digits=8, decimal_places=2)
    attested_by_name = serializers.CharField(source='engagement_record.attested_by_user.username')
    attested_at = serializers.DateTimeField(source='engagement_record.attested_at')

    class Meta:
        model = Certificate
        fields = [
            'id', 'volunteer_name', 'organization_name', 'role_title',
            'start_date', 'end_date', 'total_hours', 'attested_by_name',
            'attested_at', 'skill_summary_text', 'pdf_file', 'issued_at',
            'revoked', 'revoked_reason'
        ]
