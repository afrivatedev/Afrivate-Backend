from rest_framework.permissions import BasePermission
from .models import Organization


class IsOrganizationOwner(BasePermission):
    """Allows access only to the user who created the organization."""

    message = "Only the organization's creator can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.created_by_id == request.user.id


class IsOrganizationMember(BasePermission):
    """Allows access to the organization's creator or any of its representatives
    (at any verification status — this gates visibility, not attestation rights).

    A suspended or pending-review organization is hidden from every member —
    creator and representatives alike. Previously this check only ran on the
    creator branch, so a representative could still view a suspended org while
    its own creator was locked out.
    """

    message = "You do not have access to this organization."

    def has_object_permission(self, request, view, obj):
        is_member = (
            obj.created_by_id == request.user.id
            or obj.representatives.filter(user=request.user).exists()
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

