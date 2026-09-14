import logging

import cloudinary.utils
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers

from .models import (
    Organization,
    OrganizationDocument,
    OrganizationSocialLink,
    OrganizationRepresentative,
    OrganizationVouch,
)
from .storage import PRIVATE_DELIVERY_TYPE
from .validators import validate_org_document, validate_appointment_letter

logger = logging.getLogger(__name__)


def normalize_and_validate_url(value):
    """Prepend https:// to a scheme-less URL, then validate it.
    """
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    try:
        URLValidator()(value)
    except DjangoValidationError:
        raise serializers.ValidationError("Enter a valid URL.")
    return value


class SignedPrivateFileField(serializers.FileField):
    """Read-aware field generating a signed Cloudinary URL for the 'authenticated'
    delivery type used by PrivateRawMediaCloudinaryStorage. Mirrors
    profiles.serializers.SignedCloudinaryFileField, but that field hardcodes
    type="upload" — the wrong delivery type for these private uploads, which
    would 404 against Cloudinary if reused as-is."""

    def to_representation(self, value):
        if not value or not hasattr(value, 'name') or not value.name:
            return None
        try:
            url, _ = cloudinary.utils.cloudinary_url(
                value.name,
                resource_type="raw",
                type=PRIVATE_DELIVERY_TYPE,
                sign_url=True,
                secure=True,
            )
            return url
        except Exception as e:
            logger.error(f"Cloudinary Signature Error: {e}")
            return None


class OrganizationSocialLinkSerializer(serializers.ModelSerializer):
    """serializer for an organization's social link"""

    url = serializers.CharField(max_length=300)

    class Meta:
        model = OrganizationSocialLink
        fields = ("id", "platform", "url", "activity_verified")
        read_only_fields = ("id", "activity_verified")

    def validate_url(self, value):
        return normalize_and_validate_url(value)


class OrganizationDocumentSerializer(serializers.ModelSerializer):
    """serializer for an organization document upload"""

    file = SignedPrivateFileField(required=True)

    class Meta:
        model = OrganizationDocument
        fields = ("id", "document_type", "file", "uploaded_at", "review_status")
        read_only_fields = ("id", "uploaded_at", "review_status")

    def validate(self, attrs):
        document_type = attrs.get("document_type") or getattr(self.instance, "document_type", None)
        file = attrs.get("file")
        if file is not None and document_type:
            validate_org_document(file, document_type)
        return attrs


class OrganizationRepresentativeSerializer(serializers.ModelSerializer):
    """serializer for an organization representative registration"""

    appointment_letter = SignedPrivateFileField(required=False, allow_null=True)
    social_media_url = serializers.CharField(max_length=300)

    class Meta:
        model = OrganizationRepresentative
        fields = (
            "id",
            "full_name",
            "role_title",
            "work_email",
            "appointment_letter",
            "phone_number",
            "social_media_url",
            "verification_status",
            "created_at",
        )
        read_only_fields = ("id", "verification_status", "created_at")

    def validate_social_media_url(self, value):
        return normalize_and_validate_url(value)

    def validate_appointment_letter(self, value):
        if value is not None:
            validate_appointment_letter(value)
        return value

    def validate(self, attrs):
        work_email = attrs.get("work_email") or getattr(self.instance, "work_email", None)
        appointment_letter = attrs.get("appointment_letter") or getattr(self.instance, "appointment_letter", None)
        if not work_email and not appointment_letter:
            raise serializers.ValidationError(
                "Provide either a work email on the organization's domain, or an appointment/"
                "introduction letter proving your affiliation with this organization."
            )
        return attrs


class OrganizationRepresentativeSummarySerializer(serializers.ModelSerializer):
    """lightweight representative serializer, nested inside OrganizationSerializer"""

    class Meta:
        model = OrganizationRepresentative
        fields = ("id", "full_name", "role_title", "verification_status")


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """serializer for onboarding a new organization (PRD Sprint 1)"""

    website = serializers.CharField(max_length=300, required=False, allow_blank=True)

    class Meta:
        model = Organization
        fields = ("id", "name", "organization_type", "country", "description", "location", "website")
        read_only_fields = ("id",)

    def validate_website(self, value):
        return normalize_and_validate_url(value) if value else value


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """serializer for an organization owner editing their org's core profile.

    scuml_id lives here rather than at creation — PRD 5.1 treats it as an
    optional add-on submitted whenever the org is ready, the same shape as
    documents/social links being added after the initial onboarding step."""

    website = serializers.CharField(max_length=300, required=False, allow_blank=True)

    class Meta:
        model = Organization
        fields = ("name", "description", "location", "country", "website", "scuml_id")

    def validate_website(self, value):
        return normalize_and_validate_url(value) if value else value

    def validate_scuml_id(self, value):
        if value and self.instance.organization_type != Organization.OrgType.NGO:
            raise serializers.ValidationError(
                "SCUML only applies to NGOs — this field isn't relevant for this organization's type."
            )
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    """read serializer for an organization's full profile"""

    documents = OrganizationDocumentSerializer(many=True, read_only=True)
    social_links = OrganizationSocialLinkSerializer(many=True, read_only=True)
    representatives = OrganizationRepresentativeSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "organization_type",
            "country",
            "description",
            "location",
            "website",
            "scuml_id",
            "scuml_verified_at",
            "tier",
            "tier_status",
            "created_at",
            "documents",
            "social_links",
            "representatives",
        )
        read_only_fields = fields


class OrganizationVouchSerializer(serializers.ModelSerializer):
    """serializer for a Tier 2 vouch (PRD 5.2, Sprint 4). `to_organization` comes
    from the URL, not the payload — see views.OrganizationVouchCreateView."""

    from_organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    class Meta:
        model = OrganizationVouch
        fields = ("id", "from_organization", "to_organization", "vouch_text", "created_at")
        read_only_fields = ("id", "to_organization", "created_at")


# --- Admin-facing serializers (Sprint 3) ---------------------------------
# Expose fields never surfaced to the organization itself (registry/SCUML
# verification state, internal notes, incoming vouches) and full contact
# detail on representatives, for the admin review workflow in views_admin.py.

class OrganizationQueueSerializer(serializers.ModelSerializer):
    """lightweight row for the admin pending-review queue"""

    class Meta:
        model = Organization
        fields = ("id", "name", "organization_type", "country", "tier", "tier_status", "created_at")


class OrganizationVouchSummarySerializer(serializers.ModelSerializer):
    from_organization_name = serializers.CharField(source='from_organization.name', read_only=True)

    class Meta:
        model = OrganizationVouch
        fields = ("id", "from_organization", "from_organization_name", "vouch_text", "created_at")


class OrganizationAdminSerializer(OrganizationSerializer):
    """full detail view for admin review — adds registry/SCUML state, internal
    notes, and incoming vouches on top of the self-service OrganizationSerializer."""

    vouches_received = OrganizationVouchSummarySerializer(many=True, read_only=True)

    class Meta(OrganizationSerializer.Meta):
        fields = OrganizationSerializer.Meta.fields + (
            "registry_type",
            "registry_id",
            "registry_verified_at",
            "tier_2_admin_approved",
            "verification_notes",
            "vouches_received",
        )
        read_only_fields = fields


class OrganizationRepresentativeQueueSerializer(serializers.ModelSerializer):
    """lightweight row for the admin representative-review queue"""

    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = OrganizationRepresentative
        fields = ("id", "organization", "organization_name", "full_name", "role_title", "verification_status", "created_at")


class OrganizationRepresentativeAdminSerializer(serializers.ModelSerializer):
    """full detail view for admin review — includes contact info and internal
    verification fields never exposed via OrganizationRepresentativeSummarySerializer."""

    appointment_letter = SignedPrivateFileField(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = OrganizationRepresentative
        fields = (
            "id",
            "organization",
            "organization_name",
            "full_name",
            "role_title",
            "work_email",
            "appointment_letter",
            "phone_number",
            "social_media_url",
            "verification_status",
            "verification_method",
            "verification_call_notes",
            "verified_at",
            "created_at",
        )
        read_only_fields = fields
