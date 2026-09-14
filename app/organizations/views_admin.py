"""
Admin verification workflow — PRD §8, Sprint 3.

Gated by AdminUser auth (adminpanel's separate JWT stack), not the platform
JWT — mirrors every other admin-facing surface in adminpanel/views_*.py, and
is registered under api/admin/ in adminpanel/urls.py rather than here.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from adminpanel.views_directory import AdminAPIView, DirectoryPagination
from notifications.models import Notification

from .models import (
    Organization,
    OrganizationDocument,
    OrganizationRepresentative,
    OrganizationSocialLink,
    VerificationAuditLog,
)
from .serializers import (
    OrganizationAdminSerializer,
    OrganizationQueueSerializer,
    OrganizationRepresentativeAdminSerializer,
    OrganizationRepresentativeQueueSerializer,
)

VALID_APPROVAL_TIERS = {Organization.Tier.TIER_1, Organization.Tier.TIER_2}
VALID_VERIFICATION_METHODS = set(OrganizationRepresentative.VerificationMethod.values)


def _log(entity_type, entity_id, action, admin, notes=""):
    return VerificationAuditLog.objects.create(
        entity_type=entity_type, entity_id=str(entity_id), action=action,
        performed_by_admin=admin, notes=notes,
    )


def _notify(user, title, message):
    if user is None:
        return
    Notification.objects.create(
        recipient=user, title=title, message=message[:300], type='personal', priority='info',
    )


class OrganizationQueueView(AdminAPIView):
    """GET /api/admin/organizations/queue/ — orgs awaiting review, oldest first
    (PRD §8 item 1)."""

    def get(self, request):
        qs = Organization.objects.filter(
            tier_status=Organization.TierStatus.PENDING_REVIEW
        ).order_by('created_at')
        paginator = DirectoryPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(OrganizationQueueSerializer(page, many=True).data)


class OrganizationAdminDetailView(AdminAPIView):
    """GET /api/admin/organizations/<org_id>/ — full profile for review, with
    documents/social links/representatives/vouches side by side (PRD §8 item 2)."""

    def get(self, request, org_id):
        organization = get_object_or_404(
            Organization.objects.prefetch_related(
                'documents', 'social_links', 'representatives', 'vouches_received'
            ),
            id=org_id,
        )
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationApproveView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/approve/ {tier, notes} — assigns
    a tier. Never silent (PRD §8 item 7): always writes to VerificationAuditLog."""

    def post(self, request, org_id):
        tier = request.data.get('tier')
        notes = (request.data.get('notes') or '').strip()
        if tier not in VALID_APPROVAL_TIERS:
            return Response(
                {'detail': f"tier must be one of {sorted(VALID_APPROVAL_TIERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = get_object_or_404(Organization, id=org_id)
        organization.tier = tier
        organization.tier_status = Organization.TierStatus.ACTIVE
        if tier == Organization.Tier.TIER_2:
            organization.tier_2_admin_approved = True
        organization.save(update_fields=['tier', 'tier_status', 'tier_2_admin_approved', 'updated_at'])

        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.TIER_UPGRADED, request.user, notes,
        )
        _notify(
            organization.created_by, "Your organization has been verified",
            f"{organization.name} is now {organization.get_tier_display()}.",
        )
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationRejectView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/reject/ {reason}"""

    def post(self, request, org_id):
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'detail': 'A reason is required to reject an organization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = get_object_or_404(Organization, id=org_id)
        organization.tier_status = Organization.TierStatus.REJECTED
        organization.save(update_fields=['tier_status', 'updated_at'])

        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.REJECTED, request.user, reason,
        )
        _notify(organization.created_by, "Your organization submission was rejected", reason)
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationRequestInfoView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/request-info/ {message} — the
    third action PRD §8 item 6 requires alongside approve/reject. Doesn't
    change tier/status, so it's logged but doesn't move the review queue."""

    def post(self, request, org_id):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'detail': 'A message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        organization = get_object_or_404(Organization, id=org_id)
        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.INFO_REQUESTED, request.user, message,
        )
        _notify(organization.created_by, f"More information needed for {organization.name}", message)
        return Response({'detail': 'Request sent.'})


class OrganizationSuspendView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/suspend/ {reason} — PRD §9
    downgrade path, triggered by a report/dispute or fraud finding."""

    def post(self, request, org_id):
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'detail': 'A reason is required to suspend an organization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = get_object_or_404(Organization, id=org_id)
        if organization.tier_status == Organization.TierStatus.SUSPENDED:
            return Response(
                {'detail': 'Organization is already suspended.'}, status=status.HTTP_400_BAD_REQUEST
            )

        organization.tier_status = Organization.TierStatus.SUSPENDED
        organization.save(update_fields=['tier_status', 'updated_at'])

        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.SUSPENDED, request.user, reason,
        )
        _notify(organization.created_by, "Your organization has been suspended", reason)
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationReinstateView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/reinstate/ {reason}"""

    def post(self, request, org_id):
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'detail': 'A reason is required to reinstate an organization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = get_object_or_404(Organization, id=org_id)
        if organization.tier_status != Organization.TierStatus.SUSPENDED:
            return Response(
                {'detail': 'Organization is not suspended.'}, status=status.HTTP_400_BAD_REQUEST
            )

        organization.tier_status = Organization.TierStatus.ACTIVE
        organization.save(update_fields=['tier_status', 'updated_at'])

        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.REINSTATED, request.user, reason,
        )
        _notify(organization.created_by, "Your organization has been reinstated", reason)
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationScumlVerifyView(AdminAPIView):
    """POST /api/admin/organizations/<org_id>/scuml/verify/ — the one Tier 1
    sub-step with no public lookup API (PRD §5.1 step 2): admin manually
    confirms a voluntarily-submitted SCUML certificate. Optional add-on,
    never a precondition for Tier 1 — see PRD §9's Tier 2 -> Tier 1 note."""

    def post(self, request, org_id):
        organization = get_object_or_404(Organization, id=org_id)
        if not organization.scuml_id:
            return Response(
                {'detail': 'This organization has not submitted a SCUML ID.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization.scuml_verified_at = timezone.now()
        organization.save(update_fields=['scuml_verified_at', 'updated_at'])

        _log(
            VerificationAuditLog.EntityType.ORGANIZATION, organization.id,
            VerificationAuditLog.Action.APPROVED, request.user, "SCUML certificate confirmed.",
        )
        return Response(OrganizationAdminSerializer(organization).data)


class OrganizationDocumentReviewView(AdminAPIView):
    """POST /api/admin/organizations/documents/<doc_id>/review/ {status} —
    the inline document review action (PRD §8 items 2-3)."""

    def post(self, request, doc_id):
        review_status = request.data.get('status')
        valid = (OrganizationDocument.ReviewStatus.APPROVED, OrganizationDocument.ReviewStatus.REJECTED)
        if review_status not in valid:
            return Response(
                {'detail': "status must be 'approved' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST
            )

        document = get_object_or_404(OrganizationDocument, id=doc_id)
        document.review_status = review_status
        document.reviewed_by_admin = request.user
        document.save(update_fields=['review_status', 'reviewed_by_admin'])
        return Response({'detail': 'Document reviewed.', 'review_status': document.review_status})


class OrganizationSocialLinkVerifyView(AdminAPIView):
    """POST /api/admin/organizations/social-links/<link_id>/verify/
    {activity_verified} — records the outcome of the PRD §8 item 4 checklist
    ("account active", "content matches claimed activity", "account age
    consistent"); the checklist itself is a UI judgment call over this link's
    data, not separate backend state."""

    def post(self, request, link_id):
        activity_verified = request.data.get('activity_verified')
        if not isinstance(activity_verified, bool):
            return Response(
                {'detail': 'activity_verified (boolean) is required.'}, status=status.HTTP_400_BAD_REQUEST
            )

        link = get_object_or_404(OrganizationSocialLink, id=link_id)
        link.activity_verified = activity_verified
        link.save(update_fields=['activity_verified'])
        return Response({'detail': 'Social link updated.', 'activity_verified': link.activity_verified})


class RepresentativeQueueView(AdminAPIView):
    """GET /api/admin/organizations/representatives/queue/ — reps awaiting
    verification, oldest first (PRD §8 item 1)."""

    def get(self, request):
        qs = OrganizationRepresentative.objects.filter(
            verification_status=OrganizationRepresentative.VerificationStatus.PENDING
        ).select_related('organization').order_by('created_at')
        paginator = DirectoryPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            OrganizationRepresentativeQueueSerializer(page, many=True).data
        )


class RepresentativeVerifyView(AdminAPIView):
    """POST /api/admin/organizations/representatives/<rep_id>/verify/
    {status, verification_method, call_notes} — PRD §6 verification process
    steps 1-4, logged with a call-log/notes field (PRD §8 item 5)."""

    def post(self, request, rep_id):
        new_status = request.data.get('status')
        valid = (
            OrganizationRepresentative.VerificationStatus.VERIFIED,
            OrganizationRepresentative.VerificationStatus.REJECTED,
        )
        if new_status not in valid:
            return Response(
                {'detail': "status must be 'verified' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST
            )

        methods = request.data.get('verification_method') or []
        if not isinstance(methods, list) or any(m not in VALID_VERIFICATION_METHODS for m in methods):
            return Response(
                {'detail': f"verification_method must be a list drawn from {sorted(VALID_VERIFICATION_METHODS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call_notes = (request.data.get('call_notes') or '').strip()
        if new_status == OrganizationRepresentative.VerificationStatus.REJECTED and not call_notes:
            return Response(
                {'detail': 'call_notes is required when rejecting a representative.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        representative = get_object_or_404(
            OrganizationRepresentative.objects.select_related('organization', 'user'), id=rep_id
        )
        representative.verification_status = new_status
        representative.verification_method = methods
        representative.verification_call_notes = call_notes or None
        representative.verified_by_admin = request.user
        representative.verified_at = timezone.now()
        representative.save(update_fields=[
            'verification_status', 'verification_method', 'verification_call_notes',
            'verified_by_admin', 'verified_at',
        ])

        action = (
            VerificationAuditLog.Action.APPROVED
            if new_status == OrganizationRepresentative.VerificationStatus.VERIFIED
            else VerificationAuditLog.Action.REJECTED
        )
        _log(VerificationAuditLog.EntityType.REPRESENTATIVE, representative.id, action, request.user, call_notes)
        _notify(
            representative.user,
            f"Your representative application for {representative.organization.name}",
            f"Your application is now {representative.get_verification_status_display().lower()}."
            + (f" {call_notes}" if call_notes else ""),
        )
        return Response(OrganizationRepresentativeAdminSerializer(representative).data)
