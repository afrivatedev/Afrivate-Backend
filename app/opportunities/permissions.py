from rest_framework.permissions import BasePermission, SAFE_METHODS

# write the permsissions here
def has_permission(self, request, view):

    print("USER:", request.user)
    print("AUTH:", request.user.is_authenticated)
    print("TOKEN:", request.auth)

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow creators of an opportunity to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request (GET, HEAD, OPTIONS)
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the creator of the opportunity
        # For Opportunities, the field is 'created_by'. 
        # For Applications, the field is 'user'.
        owner_field = getattr(obj, 'created_by', getattr(obj, 'user', None))
        return owner_field == request.user


class IsEnablerOrReadOnly(BasePermission):
    """
    - Anyone can READ
    - Only authenticated Enablers can CREATE
    """
    def has_permission(self, request, view):

        # Allow GET, HEAD, OPTIONS
        if request.method in SAFE_METHODS:
            return True

        # For POST, PUT, DELETE → must be logged in
        if not request.user or not request.user.is_authenticated:
            return False

        # Must be enabler
        return getattr(request.user, "role", None) == "enabler"
    
class IsPathfinder(BasePermission):
    """Strictly for Pathfinders to apply for jobs"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "pathfinder"