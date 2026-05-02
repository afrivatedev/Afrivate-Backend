from django.shortcuts import render
from django.utils import timezone

from rest_framework import viewsets, status
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .serializers import ApplicationSerializer
from .models import Application
from user_database.permissions import IsEnablerUser, IsVerifiedUser #, IsPathfinderUser
from opportunities.permissions import IsOwnerOrReadOnly, IsEnablerOrReadOnly, IsPathfinder
from notifications.models import Notification

# Create your views here.

# The pathfinders view and create their applications
# the enablers can only view applications for their opportunities

def health_check(request):
    return HttpResponse("Application app is healthy!")

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated] # Ensure only authenticated users can access
    # queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        user = self.request.user

        if getattr(self, 'swagger_fake_view', False):
            return Application.objects.none()
        
        # Healthy Practice: Optimized Queryset
        base_qs = Application.objects.select_related(
            'opportunity', 
            'user', 
            'user__profile', 
            'user__profile__pathfinder_extra'
        ).prefetch_related(
            'user__profile__pathfinder_extra__pathfinder_skills',
            'user__profile__social_links'
        )
        
        if user.role == 'enabler':
            # Enablers can see the..... applications for opportunities they created
            # return Application.objects.filter(opportunity__created_by=user)
            return base_qs.filter(opportunity__created_by=user) # Optimized with select_related and prefetch_related
        # Pathfinders see only their own applications
        # return Application.objects.filter(user=user)
        return base_qs.filter(user=user) 
    
    def get_permissions(self):
        # BASE RULE: Everyone hitting this endpoint must be logged in AND verified
        base = [IsAuthenticated(), IsVerifiedUser()]
        
        if self.action == 'create':
            return base + [IsPathfinder()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return base + [IsOwnerOrReadOnly()]
        if self.action == 'change_status':
            return base + [IsEnablerUser()] # Replaced with IsEnablerUser to match your @action
            
        # For list and retrieve (GET requests), just use the base rules
        return base

    def perform_create(self, serializer):
        user = self.request.user
        opportunity = serializer.validated_data.get('opportunity')

        # unique_together on the model would raise an IntegrityError on duplicate;
        # this explicit check returns a clean 400 instead of a 500.
        if Application.objects.filter(user=user, opportunity=opportunity).exists():
            raise ValidationError({"detail": "You have already applied for this opportunity."})

        application = serializer.save(user=user)

        # Targeted notification to the enabler — recipient set to opportunity owner
        # so only that enabler sees this in their notification feed.
        # link is a frontend route, not a backend API URL.
        Notification.objects.create(
            recipient=opportunity.created_by,
            title="New Application Received",
            message=(
                f"{user.username} has applied for your opportunity: "
                f"'{opportunity.title}'."
            ),
            type='personal',
            priority='info',
            link=f"/enabler/applicants/{opportunity.id}/",
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user

        if user.role == 'pathfinder':
            if instance.status != 'pending':
                raise ValidationError("Your application is already under review and cannot be edited.")
            if 'status' in self.request.data:
                raise ValidationError("Pathfinders cannot modify application status.")

        serializer.save()

    def perform_destroy(self, instance):
        # RULE: Allow withdrawal only if status is pending
        if instance.status != 'pending':
            raise ValidationError("Cannot withdraw an application once it is accepted/rejected.")
        instance.delete()

    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        # detail=True means self.get_object() goes through get_queryset(), which for
        # enablers returns only applications on their own opportunities — so an enabler
        # cannot change the status of another enabler's applicants.
        application = self.get_object()
        new_status = request.data.get('status')

        if new_status not in ['accepted', 'rejected']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        application.status = new_status
        application.reviewed_at = timezone.now()
        application.save()

        # Targeted notification to the pathfinder who applied.
        # Priority is 'warning' for rejections so the frontend can colour it differently.
        # link is a frontend route to the pathfinder's applications list.
        Notification.objects.create(
            recipient=application.user,
            title=f"Application {new_status.capitalize()}",
            message=(
                f"Your application for '{application.opportunity.title}' "
                f"has been {new_status}."
            ),
            type='personal',
            priority='info' if new_status == 'accepted' else 'warning',
            link="/my-applications",
        )

        return Response({'message': f'Application marked as {new_status}'})
    
# For the Pathfinder (The "Applicant" side)
# ActionOperationLogic

# CreateApplyPathfinder submits a form that creates a record in the Applications table.
# ReadBrowse FeedPathfinder queries the Opportunities table to see what’s available.
# UpdateEdit ApplicationPathfinder can update their cover letter if the status is still "Pending."
# DeleteWithdrawPathfinder deletes their record from the Applications table.

