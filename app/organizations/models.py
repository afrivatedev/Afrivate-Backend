"""
Organization Verification Layer — see AfriVate Organization Verification PRD.

Sprint 1 (org onboarding), Sprint 2 (representative registration), Sprint 3
(admin review — see views_admin.py) and Sprint 4 (Tier 2 vouching — see
OrganizationVouch and views.OrganizationVouchCreateView) are implemented.

Sprint 5 (automated CAC lookup API integration) is not implemented — it needs
a vendor decision (Dojah/Mono/Youverify) and live API credentials, neither of
which are engineering calls. Until then, `registry_verified_at` stays unwritten
and Tier 1 approval is admin sign-off on the uploaded certificate alone, exactly
as the PRD's "Note on sequencing" (5.1) describes for the pre-automation period.
"""

import os
import uuid

from django.conf import settings
from django.db import models

from adminpanel.models import AdminUser
from .storage import PrivateRawMediaCloudinaryStorage

ORG_UPLOAD_PATH = 'afrivate/organizations'


def org_document_file_path(instance, filename):
    """Generate a unique storage path for an organization document upload."""
    ext = os.path.splitext(filename)[1]
    filename = f'{uuid.uuid4()}{ext}'
    return os.path.join(ORG_UPLOAD_PATH, f'org_{instance.organization_id}', 'documents', filename)


def representative_letter_file_path(instance, filename):
    """Generate a unique storage path for a representative's appointment letter."""
    ext = os.path.splitext(filename)[1]
    filename = f'{uuid.uuid4()}{ext}'
    return os.path.join(ORG_UPLOAD_PATH, f'org_{instance.organization_id}', 'representatives', filename)


class Organization(models.Model):
    """Present the organization being onboarded and progressively verified."""

    class OrgType(models.TextChoices):
        NGO = 'ngo', 'NGO'
        COMPANY = 'company', 'Company'
        SCHOOL = 'school', 'School'
        GOVERNMENT = 'government', 'Government'
        COMMUNITY_GROUP = 'community_group', 'Community Group'
        OTHER = 'other', 'Other'

    class RegistryType(models.TextChoices):
        RC = 'rc', 'RC — Private company limited by shares'
        BN = 'bn', 'BN — Registered business name'
        IT = 'it', 'IT — Incorporated Trustees'
        OTHER = 'other', 'Other (non-Nigerian equivalent)'

    class Tier(models.TextChoices):
        TIER_1 = 'tier_1', 'Tier 1 — Registered & Verified'
        TIER_2 = 'tier_2', 'Tier 2 — Community-Referenced'
        TIER_3 = 'tier_3', 'Tier 3 — Self-Declared / Pending'

    class TierStatus(models.TextChoices):
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        ACTIVE = 'active', 'Active'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='organizations_created'
    )

    name = models.CharField(max_length=200)
    organization_type = models.CharField(max_length=20, choices=OrgType.choices, db_index=True)
    country = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(max_length=300, blank=True)

    # Tier 1 — registry verification
    registry_type = models.CharField(max_length=10, choices=RegistryType.choices, null=True, blank=True)
    registry_id = models.CharField(max_length=100, null=True, blank=True)
    registry_verified_at = models.DateTimeField(null=True, blank=True)

    # Optional NGO-only credibility signal
    scuml_id = models.CharField(max_length=100, null=True, blank=True)
    scuml_verified_at = models.DateTimeField(null=True, blank=True)

    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.TIER_3, db_index=True)
    tier_status = models.CharField(
        max_length=20, choices=TierStatus.choices, default=TierStatus.ACTIVE, db_index=True
    )

    # Tier 2 vouching path
    vouched_by_org = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='vouched_organizations'
    )

    # Internal flag to indicate if the organization has been approved by an admin for Tier 2
    tier_2_admin_approved = models.BooleanField(default=False)

    verification_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class OrganizationDocument(models.Model):
    """Present CAC/SCUML certificates, letterhead, proof-of-work uploads, etc."""

    class DocumentType(models.TextChoices):
        CAC_CERTIFICATE = 'cac_certificate', 'CAC Certificate'
        SCUML_CERTIFICATE = 'scuml_certificate', 'SCUML Certificate'
        LETTERHEAD = 'letterhead', 'Organizational Letterhead'
        PROOF_OF_WORK_PHOTO = 'proof_of_work_photo', 'Proof of Work (Photo)'
        PROOF_OF_WORK_VIDEO = 'proof_of_work_video', 'Proof of Work (Video)'
        RECOGNITION_LETTER = 'recognition_letter', 'Recognition Letter'
        OTHER = 'other', 'Other'

    class ReviewStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, db_index=True)

    file = models.FileField(
        storage=PrivateRawMediaCloudinaryStorage(),
        upload_to=org_document_file_path,
        max_length=255,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_by_admin = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_org_documents'
    )
    review_status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.organization.name}"


class OrganizationSocialLink(models.Model):
    """Present an organization's official social presence."""

    class Platform(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        FACEBOOK = 'facebook', 'Facebook'
        INSTAGRAM = 'instagram', 'Instagram'
        X = 'x', 'X'
        TIKTOK = 'tiktok', 'TikTok'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='social_links')
    platform = models.CharField(max_length=15, choices=Platform.choices)
    url = models.URLField(max_length=300)
    activity_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.organization.name} — {self.get_platform_display()}"


class OrganizationRepresentative(models.Model):
    """Present the verification of the individual attesting on an org's behalf.

    Tracked independently of the organization's own tier: a representative must
    never be able to attest engagements while pending/rejected, regardless of
    how trusted the organization itself is.
    """

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    class VerificationMethod(models.TextChoices):
        WORK_EMAIL_DOMAIN_MATCH = 'work_email_domain_match', 'Work Email Domain Match'
        DOCUMENT_REVIEW = 'document_review', 'Document Review'
        PHONE_CALL = 'phone_call', 'Phone Call'
        SOCIAL_CROSS_CHECK = 'social_cross_check', 'Social Cross-Check'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='representatives')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_representative_roles'
    )

    full_name = models.CharField(max_length=150)
    role_title = models.CharField(max_length=100)

    # At least one of work_email / appointment_letter is required — enforced in the serializer.
    work_email = models.EmailField(null=True, blank=True)
    appointment_letter = models.FileField(
        storage=PrivateRawMediaCloudinaryStorage(),
        upload_to=representative_letter_file_path,
        max_length=255,
        null=True,
        blank=True,
    )

    phone_number = models.CharField(max_length=20)
    social_media_url = models.URLField(max_length=300)

    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING, db_index=True
    )
    verified_by_admin = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_representatives'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    verification_method = models.JSONField(default=list, blank=True)
    verification_call_notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} @ {self.organization.name} ({self.verification_status})"

    @property
    def can_attest(self):
        """Whether this representative may currently attest engagements on the
        organization's behalf (PRD §6) — independent of the organization's own
        tier. No engagements/attestation system exists in this codebase yet;
        this is the single source of truth for that future gate to check."""
        return self.verification_status == self.VerificationStatus.VERIFIED


class OrganizationVouch(models.Model):
    """A Tier 1 (or admin-approved Tier 2) organization vouching for a Tier 3
    applicant (PRD §5.2 vouching path, Sprint 4). Creating one immediately
    promotes the target organization to Tier 2 — see
    views.OrganizationVouchCreateView for the eligibility checks this model
    itself doesn't enforce (those depend on both organizations' live tier).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='vouches_given'
    )
    to_organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='vouches_received'
    )
    vouch_text = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='organization_vouches_submitted',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_organization', 'to_organization')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_organization.name} vouches for {self.to_organization.name}"


class VerificationAuditLog(models.Model):
    """Present an append-only trail for org/representative verification events.

    entity_type/entity_id mirrors adminpanel.AdminActionLog's generic shape
    rather than a polymorphic FK, since there are only two possible targets.
    performed_by_admin is nullable (the PRD table omits this) because a
    `submitted` action is performed by the applicant, not an admin.
    """

    class EntityType(models.TextChoices):
        ORGANIZATION = 'organization', 'Organization'
        REPRESENTATIVE = 'representative', 'Representative'

    class Action(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        TIER_UPGRADED = 'tier_upgraded', 'Tier Upgraded'
        TIER_DOWNGRADED = 'tier_downgraded', 'Tier Downgraded'
        SUSPENDED = 'suspended', 'Suspended'
        REINSTATED = 'reinstated', 'Reinstated'
        INFO_REQUESTED = 'info_requested', 'More Information Requested'
        REVOKED = 'revoked', 'Revoked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    performed_by_admin = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verification_actions'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} on {self.entity_type} {self.entity_id}"
