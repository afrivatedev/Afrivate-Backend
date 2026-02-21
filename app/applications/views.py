from django.shortcuts import render
from django.utils import timezone

from rest_framework import generics, viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import ApplicationSerializer
from .models import Application

# Create your views here.

# The pathfinders view and create their applications
# the enablers can only view applications for their opportunities

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated] # Ensure only authenticated users can access
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Application.objects.none()

        user = self.request.user
        if user.role == 'enabler':
            # Enablers can see the..... applications for opportunities they created
            return Application.objects.filter(opportunity__created_by=user)
            # return Application.objects.filter(user=user) # was panning to filter by user
        
        # Pathfinders see only their own applications
        return Application.objects.filter(user=user)

    def perform_create(self, serializer):
        # Automatically set the user to the logged-in pathfinder
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['put'], url_path='status')
    def change_status(self, request, pk=None):
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