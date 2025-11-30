"""
The profile app handles things like the pathfinder and Enabler view as well as
government issued identifications for both pathfinder and Enabler.
"""
from profiles.models import PathfinderProfile, EnablerProfile
from profiles.serializers import (
    PathfinderProfileSerializer,
    EnablerProfileSerializer,
    PathfinderProfilePicSerializer,
    EnablerProfilePicSerializer,
)

from django.shortcuts import get_object_or_404

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import (
    viewsets,
    mixins,
    generics,
)
from rest_framework.parsers import MultiPartParser, FormParser

class BaseProfileView(mixins.CreateModelMixin,
                mixins.RetrieveModelMixin,
                mixins.UpdateModelMixin,
                generics.GenericAPIView):
    """Base Profile View for both pathfinder and Enabler."""
    # DRF expects iterables for these attributes
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PathfinderProfileAPIView(BaseProfileView):
    """
    View to handle CRUD operations on the pathfinder profile model
    front-end can send social link data as nested objects
    when creating a profile instance
    """
    serializer_class = PathfinderProfileSerializer

    def get_object(self):
        """retrieve the profile instance for the logged-in user profile."""
        user = self.request.user
        obj = get_object_or_404(PathfinderProfile, user=user)

        return obj

class EnablerProfileAPIView(BaseProfileView):
    """
    view to handle CRUD operations on the profile model
    front-end can send the social link data as nested objects
    when creating  a profile instance
    """
    serializer_class = EnablerProfileSerializer

    def get_object(self):
        """retrieve the profile instance for the logged-in user profile."""
        user = self.request.user
        obj = get_object_or_404(EnablerProfile, user=user)

        return obj

class PathfinderProfilePicAPIView(
                mixins.RetrieveModelMixin,
                mixins.UpdateModelMixin,
                generics.GenericAPIView):
    """View to handle profile picture retrieve and update for Pathfinder."""
    serializer_class = PathfinderProfilePicSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    # Only allow GET and PUT (no PATCH/partial updates)
    http_method_names = ("get", "put", "head", "options")

    def get_object(self):
        user = self.request.user
        return get_object_or_404(PathfinderProfile, user=user)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
        
class EnablerProfilePicAPIView(
                mixins.RetrieveModelMixin,
                mixins.UpdateModelMixin,
                generics.GenericAPIView):
    """View to handle profile picture retrieve and update for Enabler."""
    serializer_class = EnablerProfilePicSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    # Only allow GET and PUT (no PATCH/partial updates)
    http_method_names = ("get", "put", "head", "options")

    def get_object(self):
        user = self.request.user
        return get_object_or_404(EnablerProfile, user=user)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class CredentialViewSet(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the credential model"""
    pass

class SocialLinkViewSet(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the social link model"""

    pass