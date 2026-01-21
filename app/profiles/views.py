"""
The profile app handles things like the pathfinder and Enabler profile view as well as
government issued identifications for both pathfinder and Enabler.
"""

from profiles.models import (
    EnablerProfile,
    PathfinderProfile,
    EnablerCredential,
    Certification,
    EnablerSocialLink,
    PathfinderSocialLink,
)
from profiles.serializers import (
    EnablerProfileSerializer,
    PathfinderProfileSerializer,
    ProfilePictureSerializer,
    EnablerCredentialSerializer,
    CertificationSerializer,
    EnablerSocialLinkSerializer,
    PathfinderSocialLinkSerializer,
)

from django.shortcuts import get_object_or_404
from django.http import Http404

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import (
    viewsets,
    mixins,
    generics,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status


class BaseProfileView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    """Base Profile View for both pathfinder and Enabler."""

    # DRF expects iterables for these attributes
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """associate the profile instance with the logged-in user."""
        user = self.request.user
        serializer.save(user=user)


class EnablerProfileAPIView(BaseProfileView):
    """
    view to handle CRUD operations on the Enabler profile model
    """

    serializer_class = EnablerProfileSerializer

    def get_object(self):
        """retrieve the profile instance for the logged-in user profile."""
        user = self.request.user
        obj = get_object_or_404(EnablerProfile, user=user)
        return obj

    def perform_create(self, serializer):
        """Prevent creation if the user already has a Pathfinder profile."""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            raise Http404(
                "Cannot create Enabler profile: a Pathfinder profile already exists for this user."
            )
        super().perform_create(serializer)


class PathfinderProfileAPIView(BaseProfileView):
    """
    View to handle CRUD operations on the pathfinder profile model
    front-end can send social link data as nested objects
    when creating a profile instance
    """

    serializer_class = PathfinderProfileSerializer

    def get_object(self):
        user = self.request.user
        obj = get_object_or_404(PathfinderProfile, user=user)
        return obj

    def perform_create(self, serializer):
        """Prevent creation if the user already has a enabler profile."""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            raise Http404(
                "Cannot create Enabler profile: an enabler profile already exists for this user."
            )
        super().perform_create(serializer)


class ProfilePictureAPIView(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView
):
    """View to handle profile picture retrieve and update for the current user's Profile."""

    serializer_class = ProfilePictureSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            return user.enabler_profile
        if hasattr(user, "pathfinder_profile"):
            return user.pathfinder_profile
        raise Http404("Profile does not exist for the user, create a profile first.")

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"profile_pic": serializer.data.get("profile_pic")},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        profile_pic = request.data.get("profile_pic")
        serializer = self.get_serializer(
            instance, data={"profile_pic": profile_pic}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {"profile_pic": serializer.data.get("profile_pic")},
            status=status.HTTP_200_OK,
        )


class EnablerCredentialViewSet(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the enablers credential model"""

    serializer_class = EnablerCredentialSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        MultiPartParser,
        FormParser,
    )
    queryset = EnablerCredential.objects.all()

    # note that pk of the credential entry is sent as a reponse when created
    def get_object(self):
        """retrieve a specific credential instance for the logged-in enabler"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            obj = get_object_or_404(
                EnablerCredential,
                pk=self.kwargs.get("pk"),
                profile=user.enabler_profile,
            )
            return obj
        elif hasattr(user, "pathfinder_profile"):
            raise Http404("A pathfinder cannot create an Enabler credential.")
        raise Http404(
            "Enabler profile does not exist for the user, create a profile first."
        )

    def get_queryset(self):
        """limit the queryset to the credentials of the logged-in enabler"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            return self.queryset.filter(profile=user.enabler_profile).order_by(
                "-created_at"
            )
        return self.queryset.none()

    def perform_create(self, serializer):
        """associate the credential instance with the logged-in enabler profile"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            serializer.save(profile=user.enabler_profile)
        else:
            raise Http404(
                "Enabler profile does not exist for the user, create a profile first."
            )


class CertificationViewSet(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the certification model"""

    serializer_class = CertificationSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser,)
    queryset = Certification.objects.all()

    def get_object(self):
        """retrieve a specific certification instance for the logged-in pathfinder"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            obj = get_object_or_404(
                Certification,
                pk=self.kwargs.get("pk"),
                profile=user.pathfinder_profile,
            )
            return obj
        raise Http404(
            "Pathfinder profile does not exist for the user, create a profile first."
        )

    def get_queryset(self):
        """limit the queryset to the certifications of the logged-in pathfinder"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            return self.queryset.filter(profile=user.pathfinder_profile).order_by(
                "-created_at"
            )
        return self.queryset.none()

    def perform_create(self, serializer):
        """associate the certification instance with the logged-in pathfinder profile"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            serializer.save(profile=user.pathfinder_profile)
        else:
            raise Http404(
                "Pathfinder Profile does not exist for the user, create a profile first."
            )


class EnablerSocialLinkViewSet(viewsets.ModelViewSet):
    """model to handle CRUD operations on the social link model"""

    serializer_class = EnablerSocialLinkSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)
    queryset = EnablerSocialLink.objects.all()

    def get_object(self):
        """retrieve a specific social link instance for the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            obj = get_object_or_404(
                user.enabler_profile.social_links,
                pk=self.kwargs.get("pk"),
            )
            return obj
        raise Http404("Profile does not exist for the user, create a profile first.")

    def get_queryset(self):
        """limit the queryset to the social links of the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            return self.queryset.filter(profile=user.enabler_profile).order_by(
                "-created_at"
            )
        return self.queryset.none()

    def perform_create(self, serializer):
        """associate the social link instance with the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            serializer.save(profile=user.enabler_profile)
        else:
            raise Http404(
                "Profile does not exist for the user, create a profile first."
            )

    def perform_update(self, serializer):
        """associate the social link instance with the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "enabler_profile"):
            serializer.save(profile=user.enabler_profile)
        else:
            raise Http404(
                "Profile does not exist for the user, create a profile first."
            )


class PathfinderSocialLinkViewSet(viewsets.ModelViewSet):
    """model to handle CRUD operations on the social link model"""

    serializer_class = PathfinderSocialLinkSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)
    queryset = PathfinderSocialLink.objects.all()

    def get_object(self):
        """retrieve a specific social link instance for the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            obj = get_object_or_404(
                user.pathfinder_profile.social_links,
                pk=self.kwargs.get("pk"),
            )
            return obj
        raise Http404("Profile does not exist for the user, create a profile first.")

    def get_queryset(self):
        """limit the queryset to the social links of the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            return self.queryset.filter(profile=user.pathfinder_profile).order_by(
                "-created_at"
            )
        return self.queryset.none()

    def perform_create(self, serializer):
        """associate the social link instance with the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            serializer.save(profile=user.pathfinder_profile)
        else:
            raise Http404(
                "Profile does not exist for the user, create a profile first."
            )

    def perform_update(self, serializer):
        """associate the social link instance with the logged-in user profile"""
        user = self.request.user
        if hasattr(user, "pathfinder_profile"):
            serializer.save(profile=user.pathfinder_profile)
        else:
            raise Http404(
                "Profile does not exist for the user, create a profile first."
            )
