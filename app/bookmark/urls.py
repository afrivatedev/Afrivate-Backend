from django.urls import path
from .views import *

# write your ursls here

urlpatterns = [
    path("", health_check, name="bookmark-health-check"),

    path('opportunities/', OpportunityView.as_view(), name='opportunity-list'), # list all opportunities
    path('bookmarks/', BookmarkListCreateView.as_view(), name='bookmark-list'), # list and create bookmarks
    path('bookmarks/<int:pk>/delete/', BookmarkDeleteView.as_view(), name='bookmark-delete'), # delete bookmark
    path('opportunities/saved/', UserBookmarkListView.as_view(), name='user-bookmarks'), # list user's bookmarked opportunities
]
