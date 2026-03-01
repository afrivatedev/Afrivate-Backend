"""
The profile app handles things like the pathfinder and Enabler profile view as well as
government issued identifications for both pathfinder and Enabler.
"""
from .models import *
from .serializers import *

from django.shortcuts import get_object_or_404
from django.http import HttpResponse 

from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import (
    viewsets,
    mixins,
    generics,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

import logging

logger = logging.getLogger(__name__)

# Create your views here.
def health_check(request):
    return HttpResponse("Profiles app is healthy!")

class BaseProfileView(mixins.RetrieveModelMixin,
                mixins.UpdateModelMixin,
                generics.GenericAPIView):
    """Base Profile View for both pathfinder and Enabler."""
    # DRF expects iterables for these attributes
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


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
        profile, created = Profile.objects.get_or_create(user=user) # ensures a profile instance always exists for the user

        if user.role != "enabler":
            logger.error(f"User {user.username} with role {user.role} is trying to access Enabler profile.")
            raise PermissionDenied("Only users with Enabler role can access Enabler profiles.")
        
        # Use get_or_create so GET and PUT always find 'something' to work with
        obj, _ = EnablerProfileExtra.objects.get_or_create(profile=profile)
        # obj = get_object_or_404(EnablerProfileExtra, profile=user.profile) # 
        return obj

class PathfinderProfileAPIView(BaseProfileView):
    """
    View to handle CRUD operations on the pathfinder profile model
    front-end can send social link data as nested objects
    when creating a profile instance
    """
    serializer_class = PathfinderProfileSerializer
    permission_classes = (IsAuthenticated, )
    authentication_classes = (JWTAuthentication, )

    def get_object(self):
        user = self.request.user
        profile, created = Profile.objects.get_or_create(user=user) # ensures a profile instance always exists for the user
        
        if user.role != "pathfinder":  
            logger.error(f"User {user.username} with role {user.role} is trying to access Pathfinder profile.")
            raise PermissionDenied("Only users with Pathfinder role can access Pathfinder profiles.")
        
        obj, _ = PathfinderProfileExtra.objects.get_or_create(profile=profile)
        return obj # get_object_or_404(PathfinderProfileExtra, profile=user.profile)

class ProfilePictureAPIView(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            generics.GenericAPIView):
    """View to handle profile picture retrieve and update for the current user's Profile."""
    serializer_class = ProfilePictureSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    http_method_names = ("get", "put", "patch", "head", "options")

    def get_object(self):
        user = self.request.user
        return get_object_or_404(Profile, user=user)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class CredentialViewSet(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the credential model"""
    serializer_class = CredentialSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get_queryset(self):
        """return credentials for the logged-in user"""

        if getattr(self, 'swagger_fake_view', False):
            return Credential.objects.none()
    
        user = self.request.user
        return user.profile.credentials.all()
        # return Credential.objects.filter(profile=user.profile)
    
    def perform_create(self, serializer):
        """associate the credential with the logged-in user's profile"""
        user = self.request.user
        logger.info("Creating credential for user: %s", user.username)
        logger.info("Profile: %s", user.profile)
        logger.info("Request FILES: %s", self.request.FILES)  # check the file is actually arriving
        serializer.save(profile=user.profile)

class SocialLinkViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD for social links. 
    Limits access so users only interact with their own links.
    """
    serializer_class = SocialLinkSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [JWTAuthentication,]

    def get_queryset(self):
        # If the link doesn't belong to the user's profile, it "doesn't exist" (404).
        if getattr(self, 'swagger_fake_view', False):
            return SocialLink.objects.none()
    
        return SocialLink.objects.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        # Explicitly attach the link to the current user's profile
        serializer.save(profile=self.request.user.profile)

class PathfinderViewSet(ListAPIView):
    """a model viewset to handle CRUD operations on the pathfinder skill, education and certification models"""
    serializer_class = PathfinderProfileSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get_queryset(self):
        """return pathfinder skills, education and certifications for the logged-in user"""
        if getattr(self, 'swagger_fake_view', False):
            return PathfinderProfileExtra.objects.none()

        user = self.request.user
        return PathfinderProfileExtra.objects.filter(profile=user.profile)
    
class PublicEnablerProfileView(generics.RetrieveAPIView):
    """allows any authenticated user to view an enabler's public profile"""
    serializer_class = EnablerProfileSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get_object(self):
        user_id = self.kwargs['user_id']
        return get_object_or_404(EnablerProfileExtra, profile__user__id=user_id)