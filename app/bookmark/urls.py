from django.urls import path
from .views import *

# write your ursls here

urlpatterns = [
    path("", health_check, name="bookmark-health-check"),

        # bookmarks
    path('opportunities/saved/', BookmarkListCreateView.as_view(), name='bookmark-list'), # list and create bookmarks
    path('opportunities/saved/<int:opportunity_id>/', BookmarkDeleteView.as_view(), name='bookmark-delete'), # delete bookmark
    # path('opportunities/saved/', UserBookmarkListView.as_view(), name='user-bookmarks'), # list user's bookmarked opportunities
    
    path('applicants/saved/', PathfinderBookmarkView.as_view(), name='pathfinder-bookmarks'), # list and create pathfinder bookmarks
    path('applicants/saved/<int:pathfinder_id>/', PathfinderBookmarkDeleteView.as_view(), name='pathfinder-bookmark-delete'), # delete pathfinder bookmark

    path('enablers/saved/', EnablerBookmarkView.as_view(), name='enabler-bookmarks'),
    path('enablers/saved/<int:enabler_id>/', EnablerBookmarkDeleteView.as_view(), name='enabler-bookmark-delete'),
]
