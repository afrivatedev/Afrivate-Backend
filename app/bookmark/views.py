# from django.shortcuts import render
from django.http import HttpResponse #, JsonResponse
# from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
# from rest_framework import filters
from rest_framework.pagination import PageNumberPagination

from .serializers import BookmarkSerializer
from .models import Bookmark
import logging

logger = logging.getLogger(__name__)

# Create your views here.
def health_check(request):
    logger.info("Health check requested.")
    return HttpResponse("Bookmark app is running.")

class StandardResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


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

