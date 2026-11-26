from rest_framework.permissions import BasePermission
from .models import Organization, OrganizationRepresentative


class IsOrganizationOwner(BasePermission):
    """Allows access only to the user who created the organization."""

    message = "Only the organization's creator can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.created_by_id == request.user.id


class IsOrganizationMember(BasePermission):
    """Allows access to the organization's creator or a VERIFIED representative.

    A pending or rejected representative applicant is not a member: they can
    see only their own application (GET /representatives/me/), not the
    organization's documents, representatives or contact details.

    A suspended or pending-review organization is hidden from every member —
    creator and representatives alike.
    """

    message = "You do not have access to this organization."

    def has_object_permission(self, request, view, obj):
        is_member = (
            obj.created_by_id == request.user.id
            or obj.representatives.filter(
                user=request.user,
                verification_status=OrganizationRepresentative.VerificationStatus.VERIFIED,
            ).exists()
        )
        if not is_member:
            return False

        if obj.tier_status == Organization.TierStatus.SUSPENDED:
            self.message = "This organization is suspended."
            return False
        if obj.tier_status == Organization.TierStatus.PENDING_REVIEW:
            self.message = "This organization is pending approval."
            return False
        return True

