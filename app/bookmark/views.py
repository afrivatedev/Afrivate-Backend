from django.http import HttpResponse 

from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .serializers import BookmarkSerializer, BookmarkUserSerializer
from .models import Bookmark, BookmarkUser
from .permissions import IsEnablerUser
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
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        user = self.request.user
        return Bookmark.objects.filter(user=user).select_related('opportunity')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# remove opportunity (unbookmark) /api/bookmarks/{opportunity_id}/ DELETE {204 No Content}
class BookmarkDeleteView(DestroyAPIView):
    """ Remove a bookmarked opportunity for the authenticated user.
     DELETE /api/bookmarks/{bookmark_id}/
     """
    # serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'opportunity_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Bookmark.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Bookmark.objects.none()
        return Bookmark.objects.filter(user=user)


class PathfinderBookmarkView(ListCreateAPIView):
    permission_classes = [IsEnablerUser]
    serializer_class = BookmarkUserSerializer

    def get_queryset(self):
        # Only show the bookmarks created by THIS enabler
        user = self.request.user

        return BookmarkUser.objects.filter(
            enabler=user
        ).select_related('pathfinder', 'pathfinder__user')

    def perform_create(self, serializer):
        serializer.save(enabler=self.request.user)

class PathfinderBookmarkDeleteView(DestroyAPIView):
    permission_classes = [IsEnablerUser]
    lookup_field = 'pathfinder_id' # Allows deleting by the Pathfinder's User ID

    def get_queryset(self):
        return BookmarkUser.objects.filter(enabler=self.request.user)