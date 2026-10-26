from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from .models import Opportunity

# write serializers here
class OpportunitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()
    is_external = serializers.BooleanField(read_only=True)
    work_mode = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        if obj.created_by_id is None:
            # Scraped listing: no Afrivate owner, so show the hiring organisation.
            return obj.organization_name or None
        try:
            return obj.created_by.profile.enabler_extra.name
        except Exception:
            return obj.created_by.username

    def get_work_mode(self, obj):
        # Enablers describe work mode inside the description; only scraped listings carry it as data.
        if not obj.is_external:
            return None
        return 'Remote' if obj.is_remote else 'On-site'

    def get_applications_count(self, obj):
        return obj.applicants.count()


    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'opportunity_type', 'description',
            'link', 'posted_at', 'is_open', 'created_by_name', 'created_by',
            'target_applicants', 'applications_count',
            # Scraped listings (blank/null for opportunities posted by enablers)
            'is_external', 'source', 'organization_name', 'location', 'work_mode',
            'deadline', 'field',
        ]

        read_only_fields = [
            'created_by', 'posted_at', 'source', 'organization_name', 'location', 'deadline', 'field',
        ]
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
        # Edit window check runs only on updates (self.instance is set).
        # Content edits are locked 12 hours after posting (Opportunity.can_edit),
        # but changing is_open (close/reopen) stays allowed at any age — it's
        # lifecycle management, and DELETE already closes posts with applicants
        # regardless of how old they are.
        if self.instance and not self.instance.can_edit():
            changed_content_fields = [
                field for field, value in data.items()
                if field != 'is_open' and getattr(self.instance, field) != value
            ]
            if changed_content_fields:
                raise serializers.ValidationError(
                    "The edit window for this opportunity has closed (12h limit)."
                )
        return data
