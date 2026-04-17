# from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import ValidationError

from .models import Opportunity
from applications.models import Application
from profiles.models import PathfinderProfileExtra
from bookmark.models import Bookmark
from .serializers import OpportunitySerializer
from profiles.serializers import ApplicantProfileSerializer
from applications.serializers import ApplicationListSerializer
from .permissions import IsEnablerOrReadOnly, IsOwnerOrReadOnly, IsOpportunityOwner

from user_database.permissions import IsVerifiedUser

import logging
logger = logging.getLogger(__name__)

# Create your views here

def health_check(request):
    return HttpResponse("Opportunities app is healthy!")

def admin_opportunity_list(request):
    """ Admin interface to list all opportunities with their bookmark counts. """
    opportunities = Opportunity.objects.all().order_by('-posted_at')
    data = []
    for opp in opportunities:
        bookmark_count = Bookmark.objects.filter(opportunity=opp).count()
        data.append({
            'id': opp.id,
            'title': opp.title,
            'opportunity_type': opp.opportunity_type,
            'is_open': opp.is_open,
            'posted_at': opp.posted_at,
            'created_by': opp.created_by.username,
            'bookmark_count': bookmark_count,
        })
    return JsonResponse(data, safe=False)

class StandardResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# list all opportunities /api/opportunities/ GET {200}
class OpportunityView(ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsVerifiedUser(), IsEnablerOrReadOnly()]
        return [IsEnablerOrReadOnly()]
    

    queryset = Opportunity.objects.select_related('created_by').order_by('-posted_at')
    serializer_class = OpportunitySerializer 
    pagination_class = StandardResultsPagination
    permission_classes = [IsOwnerOrReadOnly, IsEnablerOrReadOnly] # Only enablers can create
    
    # Enable Search and Category Filtering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['opportunity_type', 'is_open'] # Exact matches
    search_fields = ['title', 'description'] # Partial text search

    def perform_create(self, serializer):
        # Automatically set created_by to the logged-in user (the "Enabler")
        serializer.save(created_by=self.request.user)

# Specifically for the "My Posted Opportunities" page
class EnablerOpportunityListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    serializer_class = OpportunitySerializer

    def get_queryset(self):
        # Only show opportunities created by the logged-in user
        return Opportunity.objects.filter(created_by=self.request.user).select_related('created_by')
    
# For the Pathfinder (The "Job Seeker" side)    
class OpportunityDetailView(RetrieveUpdateDestroyAPIView):
    """
    Handles GET (Retrieve), PUT/PATCH (Update), and DELETE for a single opportunity.
    Enforces the IsOwnerOrReadOnly permission.
    """
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsVerifiedUser(), IsOwnerOrReadOnly(), IsEnablerOrReadOnly()]
        return []


    def perform_update(self, serializer):
        if self.request.user.role != 'enabler':
            raise PermissionDenied("Only Enablers can edit opportunities.")
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.applicants.exists():
            instance.is_open = False
            instance.save()
            return Response(
                {"message": "Opportunity has applicants and cannot be deleted. It has been closed instead."},
                status=status.HTTP_200_OK
            )
        self.perform_destroy(instance)
        return Response(
            {"message": "Opportunity deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

    def perform_destroy(self, instance):
        if instance.applicants.exists():
            # If applicants exist, we just cloe it instead
            instance.is_open = False
            instance.save()

            return
        instance.delete()

# admin interface with all opportunities and their bookmark counts

# For the Enabler (The "Employer" side)
# ActionOperationLogic
# CreatePost OpportunityEnabler fills a form to add a new record to the Opportunities table.
# ReadView ApplicantsEnabler views all Applications linked to their specific opportunity_id.
# UpdateEdit PostingEnabler modifies the description or changes the application status (e.g., "Accepted").
# DeleteRemove PostingEnabler deletes an opportunity (usually "soft delete" or archiving is better).


class OpportunityApplicantListView(ListAPIView):
    """enabler views all applicants for their opportunity"""
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsOpportunityOwner]
    serializer_class = ApplicationListSerializer

    def get_queryset(self):
        logger.info(f"Fetching applicants for opportunity ID: {self.kwargs['pk']} by user: {self.request.user.username}")
        opportunity_id = self.kwargs['pk']
        return Application.objects.filter(opportunity_id=opportunity_id).select_related('user')


class ApplicantProfileView(RetrieveAPIView):
    """enabler views a specific applicant's full pathfinder profile"""
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsOpportunityOwner]
    serializer_class = ApplicantProfileSerializer

    def get_object(self):
        logger.info(f"Fetching profile for applicant ID: {self.kwargs['applicant_id']} for opportunity ID: {self.kwargs['pk']} by user: {self.request.user.username}")
        opportunity_id = self.kwargs['pk']
        applicant_id = self.kwargs['applicant_id']

        application = Application.objects.filter(
            opportunity_id=opportunity_id,
            user_id=applicant_id
        ).select_related(
            'user__profile__pathfinder_extra'
        ).first()
        logger.info(f"Application query result: {application}")

        if not application:
            logger.warning(f"No application found for applicant ID: {applicant_id} to opportunity ID: {opportunity_id}")
            raise NotFound("This applicant did not apply to this opportunity.")

        try:
            return application.user.profile.pathfinder_extra
        except PathfinderProfileExtra.DoesNotExist:
            raise NotFound("This applicant has not set up a pathfinder profile yet.")