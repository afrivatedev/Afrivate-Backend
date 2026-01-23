from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import logging
from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated

from .serializers import BookmarkSerializer, OpportunitySerializer
from .models import Bookmark, Opportunity

logger = logging.getLogger(__name__)

# Create your views here.
def health_check(request):
    logger.info("Health check requested.")
    return HttpResponse("Bookmark app is running.")

# list all opportunities /api/opportunities/ GET {200}
class OpportunityView(ListCreateAPIView):
    queryset = Opportunity.objects.all().order_by('-posted_at')
    serializer_class = OpportunitySerializer 

# save opportunity (bookmark) /api/bookmarks/ POST {200}
class BookmarkListCreateView(ListCreateAPIView):
    """"""
    permission_classes = [IsAuthenticated]
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
        return Bookmark.objects.filter(user=self.request.user)



# admin interface with all opportunities and their bookmark counts