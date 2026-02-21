from rest_framework.permissions import BasePermission

# write your permissions here. 
class IsEnablerUser(BasePermission):
    """Allows access only to Enabler users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'enabler')

class IsPathfinderUser(BasePermission):
    """Allows access only to Pathfinder users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'pathfinder')
    
