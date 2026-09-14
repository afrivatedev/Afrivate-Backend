from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.generics import  *
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from notifications.models import Notification
from user_database.permissions import IsEnablerUser, IsVerifiedUser

from .models import (
    Organization,
    OrganizationDocument,
    OrganizationSocialLink,
    OrganizationRepresentative,
    OrganizationVouch,
    VerificationAuditLog,
)
from .permissions import IsOrganizationOwner, IsOrganizationMember
from .serializers import *


def _log_submission(entity_type, entity_id, notes=""):
    VerificationAuditLog.objects.create(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=VerificationAuditLog.Action.SUBMITTED,
        notes=notes,
    )


class OrganizationCreateView(CreateAPIView):
    """POST /api/organizations/ — onboard a new organization (PRD Sprint 1)."""

    permission_classes = [IsAuthenticated, IsVerifiedUser, IsEnablerUser]
    serializer_class = OrganizationCreateSerializer
    throttle_scope = 'org_create'

    def perform_create(self, serializer):
        organization = serializer.save(
            created_by=self.request.user,
            tier=Organization.Tier.TIER_3,
            tier_status=Organization.TierStatus.ACTIVE,
        )
        _log_submission(VerificationAuditLog.EntityType.ORGANIZATION, organization.id)


class MyOrganizationsView(ListAPIView):
    """GET /api/organizations/mine/ — organizations the user created or represents."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Organization.objects.none()
        user = self.request.user
        return Organization.objects.filter(
            Q(created_by=user) | Q(representatives__user=user)
        ).distinct().prefetch_related('documents', 'social_links', 'representatives')


class OrganizationDetailView(RetrieveUpdateAPIView):
    """GET, PATCH /api/organizations/<id>/ — org profile detail / edit."""

    permission_classes = [IsAuthenticated]
    queryset = Organization.objects.all()

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return OrganizationUpdateSerializer
        return OrganizationSerializer

    def get_object(self):
        obj = super().get_object()
        if self.request.method in ('PATCH', 'PUT'):
            self.check_object_permissions_extra(obj, IsOrganizationOwner())
        else:
            self.check_object_permissions_extra(obj, IsOrganizationMember())
        return obj

    def check_object_permissions_extra(self, obj, permission):
        if not permission.has_object_permission(self.request, self, obj):
            raise PermissionDenied(getattr(permission, 'message', None))


def _get_member_organization(request, org_id):
    """Fetch an organization by id and enforce IsOrganizationMember access."""
    organization = get_object_or_404(Organization, id=org_id)
    if not IsOrganizationMember().has_object_permission(request, None, organization):
        raise PermissionDenied("You do not have access to this organization.")
    return organization


class OrganizationDocumentListCreateView(ListCreateAPIView):
    """POST, GET /api/organizations/<id>/documents/ — upload/list documents."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationDocumentSerializer
    throttle_scope = 'org_document_upload'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationDocument.objects.none()
        organization = _get_member_organization(self.request, self.kwargs['org_id'])
        return organization.documents.all()

    def perform_create(self, serializer):
        organization = _get_member_organization(self.request, self.kwargs['org_id'])
        serializer.save(organization=organization)


class OrganizationDocumentDeleteView(DestroyAPIView):
    """DELETE /api/organizations/documents/<doc_id>/ — remove a still-pending document."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationDocumentSerializer
    lookup_url_kwarg = 'doc_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationDocument.objects.none()
        return OrganizationDocument.objects.filter(organization__created_by=self.request.user)

    def get_object(self):
        obj = super().get_object()
        if obj.review_status != OrganizationDocument.ReviewStatus.PENDING:
            raise PermissionDenied("A reviewed document cannot be removed.")
        return obj


class OrganizationSocialLinkListCreateView(ListCreateAPIView):
    """POST, GET /api/organizations/<id>/social-links/ — add/list social links."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSocialLinkSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationSocialLink.objects.none()
        organization = _get_member_organization(self.request, self.kwargs['org_id'])
        return organization.social_links.all()

    def perform_create(self, serializer):
        organization = _get_member_organization(self.request, self.kwargs['org_id'])
        serializer.save(organization=organization)


class OrganizationSocialLinkDetailView(RetrieveUpdateDestroyAPIView):
    """GET, PATCH, DELETE /api/organizations/social-links/<link_id>/ — the
    owner edits or removes their own link. Editing url/platform always resets
    activity_verified back to False: an admin verified the old link's actual
    content, not whatever the URL is edited to point at next, so silently
    keeping a "verified" badge on a swapped-out link would be a trust hole."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSocialLinkSerializer
    lookup_url_kwarg = 'link_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationSocialLink.objects.none()
        return OrganizationSocialLink.objects.filter(organization__created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(activity_verified=False)


class OrganizationRepresentativeListCreateView(ListCreateAPIView):
    """POST, GET /api/organizations/<id>/representatives/ — register as / list
    an organization's representatives. Anyone verified may apply to represent
    an org; impersonation is caught by admin phone/social verification
    (Sprint 3), not by gatekeeping who may apply."""

    permission_classes = [IsAuthenticated, IsVerifiedUser, IsEnablerUser]
    serializer_class = OrganizationRepresentativeSerializer
    throttle_scope = 'org_representative_register'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationRepresentative.objects.none()
        organization = _get_member_organization(self.request, self.kwargs['org_id'])
        return organization.representatives.all()

    def perform_create(self, serializer):
        organization = get_object_or_404(Organization, id=self.kwargs['org_id'])
        if OrganizationRepresentative.objects.filter(organization=organization, user=self.request.user).exists():
            raise PermissionDenied("You have already applied to represent this organization.")
        representative = serializer.save(organization=organization, user=self.request.user)
        _log_submission(VerificationAuditLog.EntityType.REPRESENTATIVE, representative.id)


class MyRepresentativeApplicationsView(ListAPIView):
    """GET /api/organizations/representatives/me/ — the requesting user's own
    representative applications, across every organization."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationRepresentativeSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationRepresentative.objects.none()
        return OrganizationRepresentative.objects.filter(user=self.request.user).select_related('organization')


class OrganizationRepresentativeRevokeView(DestroyAPIView):
    """DELETE /api/organizations/<org_id>/representatives/<rep_id>/ — the
    organization owner revokes a representative's attestation rights (PRD §10:
    "the organization must be able to revoke their attestation rights promptly").
    Distinct from admin rejection (views_admin.RepresentativeVerifyView) —
    this is the owner's own call, not a verification outcome."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationRepresentativeSerializer
    lookup_url_kwarg = 'rep_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrganizationRepresentative.objects.none()
        return OrganizationRepresentative.objects.filter(
            organization_id=self.kwargs['org_id'], organization__created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        VerificationAuditLog.objects.create(
            entity_type=VerificationAuditLog.EntityType.REPRESENTATIVE,
            entity_id=str(instance.id),
            action=VerificationAuditLog.Action.REVOKED,
            notes="Revoked by organization owner.",
        )
        instance.delete()


class OrganizationVouchCreateView(CreateAPIView):
    """POST /api/organizations/<org_id>/vouches/ — an existing Tier 1 (or
    admin-approved Tier 2) organization vouches for a Tier 3 applicant,
    immediately promoting the applicant to Tier 2 (PRD §5.2, Sprint 4).
    `org_id` in the URL is the applicant being vouched for; the vouching
    organization is identified by `from_organization` in the request body."""

    permission_classes = [IsAuthenticated, IsVerifiedUser, IsEnablerUser]
    serializer_class = OrganizationVouchSerializer
    throttle_scope = 'org_vouch'

    def perform_create(self, serializer):
        to_organization = get_object_or_404(Organization, id=self.kwargs['org_id'])
        from_organization = serializer.validated_data['from_organization']

        if from_organization.id == to_organization.id:
            raise PermissionDenied("An organization cannot vouch for itself.")

        is_creator = from_organization.created_by_id == self.request.user.id
        is_verified_rep = from_organization.representatives.filter(
            user=self.request.user,
            verification_status=OrganizationRepresentative.VerificationStatus.VERIFIED,
        ).exists()
        if not (is_creator or is_verified_rep):
            raise PermissionDenied(
                "You must be the creator or a verified representative of the vouching organization."
            )

        eligible = from_organization.tier_status == Organization.TierStatus.ACTIVE and (
            from_organization.tier == Organization.Tier.TIER_1
            or (from_organization.tier == Organization.Tier.TIER_2 and from_organization.tier_2_admin_approved)
        )
        if not eligible:
            raise PermissionDenied(
                "Only a Tier 1 organization, or a Tier 2 organization approved via admin manual "
                "review, may vouch for another organization."
            )

        if to_organization.tier != Organization.Tier.TIER_3:
            raise PermissionDenied("This organization is already at or above Tier 2.")
        if to_organization.tier_status != Organization.TierStatus.ACTIVE:
            raise PermissionDenied("This organization is not currently eligible to be vouched for.")
        if OrganizationVouch.objects.filter(
            from_organization=from_organization, to_organization=to_organization
        ).exists():
            raise PermissionDenied("This organization has already vouched for the applicant.")

        vouch = serializer.save(
            to_organization=to_organization, created_by=self.request.user,
        )

        to_organization.tier = Organization.Tier.TIER_2
        to_organization.save(update_fields=['tier', 'updated_at'])

        VerificationAuditLog.objects.create(
            entity_type=VerificationAuditLog.EntityType.ORGANIZATION,
            entity_id=str(to_organization.id),
            action=VerificationAuditLog.Action.TIER_UPGRADED,
            notes=f"Vouched for by {from_organization.name} ({from_organization.get_tier_display()}).",
        )
        Notification.objects.create(
            recipient=to_organization.created_by,
            title="Your organization reached Tier 2",
            message=(
                f"{from_organization.name} vouched for {to_organization.name}, raising it to "
                "Community-Referenced status."
            )[:300],
            type='personal',
            priority='info',
        )
        return vouch
