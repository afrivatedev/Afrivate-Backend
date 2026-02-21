# from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.generics import ListCreateAPIView #, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from .models import Opportunity
from bookmark.models import Bookmark
from .serializers import OpportunitySerializer
from .permissions import IsEnablerOrReadOnly, IsOwnerOrReadOnly

# Create your views here

def health_check():
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
    queryset = Opportunity.objects.all().order_by('-posted_at')
    serializer_class = OpportunitySerializer 
    pagination_class = StandardResultsPagination

    permission_classes = [IsEnablerOrReadOnly, IsAuthenticated] # Only enablers can create
    
    # Enable Search and Category Filtering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['opportunity_type', 'is_open'] # Exact matches
    search_fields = ['title', 'description'] # Partial text search

    def perform_create(self, serializer):
        # Automatically set created_by to the logged-in user (the "Enabler")
        serializer.save(created_by=self.request.user)

# Specifically for the "My Posted Opportunities" page
class EnablerOpportunityListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OpportunitySerializer

    def get_queryset(self):
        # Only show opportunities created by the logged-in user
        return Opportunity.objects.filter(created_by=self.request.user)

class OpportunityDetailView(RetrieveUpdateDestroyAPIView):
    """
    Handles GET (Retrieve), PUT/PATCH (Update), and DELETE for a single opportunity.
    Enforces the IsOwnerOrReadOnly permission.
    """
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
    permission_classes = [IsOwnerOrReadOnly, IsEnablerOrReadOnly]

    def perform_update(self, serializer):
        if self.request.user.role != 'enabler':
            raise PermissionDenied("Only Enablers can edit opportunities.")
        serializer.save()

    def perform_destroy(self, instance):
        # Optional: Add logic to prevent deletion if people have already applied
        if instance.applicants.count() > 0:
            # Instead of deleting, we usually just close it
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