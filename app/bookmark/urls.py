from django.urls import path
from .views import *

# write your ursls here

urlpatterns = [
    path("", health_check, name="bookmark-health-check"),

        # bookmarks
    path('opportunities/saved/', BookmarkListCreateView.as_view(), name='bookmark-list'), # list and create bookmarks
    path('bookmarks/<int:pk>/delete/', BookmarkDeleteView.as_view(), name='bookmark-delete'), # delete bookmark
    # path('opportunities/saved/', UserBookmarkListView.as_view(), name='user-bookmarks'), # list user's bookmarked opportunities
    path('applicants/saved/', PathfinderBookmarkView.as_view(), name='pathfinder-bookmarks'), # list and create pathfinder bookmarks
    path('applicants/saved/<int:pk>/delete/', PathfinderBookmarkDeleteView.as_view(), name='pathfinder-bookmark-delete'), # delete pathfinder bookmark
]
