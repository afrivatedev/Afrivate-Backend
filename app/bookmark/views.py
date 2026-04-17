from django.http import HttpResponse 

from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .serializers import BookmarkSerializer, BookmarkUserSerializer, BookmarkEnablerSerializer
from .models import Bookmark, BookmarkUser, BookmarkEnabler
from .permissions import IsEnablerUser, IsPathfinderUser

from user_database.permissions import IsVerifiedUser
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
    permission_classes = [IsAuthenticated, IsVerifiedUser] # Only authenticated users can bookmark
    serializer_class = BookmarkSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return Bookmark.objects.filter(
            user=self.request.user
        ).select_related('opportunity')

    def perform_create(self, serializer):
        if self.request.user.role != 'pathfinder':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only pathfinders can bookmark opportunities.")
        serializer.save(user=self.request.user)


# remove opportunity (unbookmark) /api/bookmarks/{opportunity_id}/ DELETE {204 No Content}
class BookmarkDeleteView(DestroyAPIView):
    """ Remove a bookmarked opportunity for the authenticated user.
    DELETE /api/bookmarks/{bookmark_id}/
    """
    # serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    serializer_class = BookmarkSerializer
    lookup_field = 'opportunity_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Bookmark.objects.none()
        return Bookmark.objects.filter(user=self.request.user)


class PathfinderBookmarkView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsEnablerUser]
    serializer_class = BookmarkUserSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        # Only show the bookmarks created by THIS enabler
        return BookmarkUser.objects.filter(
            enabler=self.request.user
        ).select_related('pathfinder__profile')

    def perform_create(self, serializer):
        serializer.save(enabler=self.request.user)

class PathfinderBookmarkDeleteView(DestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsEnablerUser]
    lookup_field = 'pathfinder_id' # Allows deleting by the Pathfinder's User ID

    def get_queryset(self):
        return BookmarkUser.objects.filter(enabler=self.request.user)
    

class EnablerBookmarkView(ListCreateAPIView):
    """Pathfinder bookmarks an enabler profile"""
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsPathfinderUser]
    serializer_class = BookmarkEnablerSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return BookmarkEnabler.objects.filter(
            pathfinder=self.request.user
        ).select_related('enabler__profile')

    def perform_create(self, serializer):
        serializer.save(pathfinder=self.request.user)

class EnablerBookmarkDeleteView(DestroyAPIView):
    """Pathfinder removes an enabler bookmark"""
    permission_classes = [IsAuthenticated, IsVerifiedUser, IsPathfinderUser]
    serializer_class = BookmarkEnablerSerializer
    lookup_field = 'enabler_id'

    def get_queryset(self):
        return BookmarkEnabler.objects.filter(pathfinder=self.request.user)