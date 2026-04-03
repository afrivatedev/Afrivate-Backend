from rest_framework import permissions, exceptions

class IsEnablerUser(permissions.BasePermission):
    """
    Allows access only to users who have an EnablerProfileExtra record.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Check if the user has an 'enabler_extra' via the profile relation
        return hasattr(request.user.profile, 'enabler_extra')
