from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from .serializers import BookmarkSerializer, OpportunitySerializer
from .models import Bookmark, Opportunity
from .permissions import IsOwnerOrReadOnly, IsEnablerOrReadOnly
import logging

logger = logging.getLogger(__name__)

# Create your views here.
def health_check(request):
    logger.info("Health check requested.")
    return HttpResponse("Bookmark app is running.")

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

# save opportunity (bookmark) /api/bookmarks/ POST {200}
class BookmarkListCreateView(ListCreateAPIView):
    """"""
    permission_classes = [IsAuthenticated] # Only authenticated users can bookmark
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        return Bookmark.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# list all bookmarked opportunities for a user /api/bookmarks/ GET {200} OR  /api/opportunities/saved/
class UserBookmarkListView(ListCreateAPIView):
    """ List all bookmarked opportunities for the authenticated user.
     GET /api/bookmarks/
     """
    permission_classes = [IsAuthenticated]
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        return Bookmark.objects.filter(user=user)

# remove opportunity (unbookmark) /api/bookmarks/{opportunity_id}/ DELETE {204 No Content}
class BookmarkDeleteView(DestroyAPIView):
    """ Remove a bookmarked opportunity for the authenticated user.
     DELETE /api/bookmarks/{bookmark_id}/
     """
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Bookmark.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Bookmark.objects.none()
        return Bookmark.objects.filter(user=user)

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
    permission_classes = [IsOwnerOrReadOnly]

# admin interface with all opportunities and their bookmark counts