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
from user_database.permissions import IsEnablerUser #, IsPathfinderUser
from opportunities.permissions import IsOwnerOrReadOnly, IsEnablerOrReadOnly, IsPathfinder

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
        if self.action == 'create':
            return [IsPathfinder()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrReadOnly()]
        if self.action == 'change_status':
            return [IsEnablerOrReadOnly()] # Only Enablers can hit the /status endpoint
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # Automatically set the user to the logged-in pathfinder
        user = self.request.user
        opportunity = serializer.validated_data.get('opportunity')

        # Check for existing application
        if Application.objects.filter(user=user, opportunity=opportunity).exists():
            raise ValidationError({"detail": "You have already applied for this opportunity."})

        serializer.save(user=user)

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

    @action(detail=True, methods=['patch'], permission_classes=[IsEnablerUser])
    def change_status(self, request, pk=None):
        # detail=True ensures this application belongs to the Enabler's opportunity 
        # because of the logic in get_queryset
        application = self.get_object()
        new_status = request.data.get('status')

        if new_status not in ['accepted', 'rejected']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        application.status = new_status
        application.reviewed_at = timezone.now()
        application.save()
        
        return Response({'message': f'Application marked as {new_status}'})
    
# For the Pathfinder (The "Applicant" side)
# ActionOperationLogic

# CreateApplyPathfinder submits a form that creates a record in the Applications table.
# ReadBrowse FeedPathfinder queries the Opportunities table to see what’s available.
# UpdateEdit ApplicationPathfinder can update their cover letter if the status is still "Pending."
# DeleteWithdrawPathfinder deletes their record from the Applications table.

