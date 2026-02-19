from django.urls import path
from .views import *

# write your urls here

urlpatterns = [
    path("", health_check, name="opportunities-health-check"),
    
    path('opportunities/', OpportunityView.as_view(), name='opportunity-list'), # list all opportunities
    path('opportunities/mine/', EnablerOpportunityListView.as_view(), name='my-opportunities'), # list opportunities created by the logged-in enabler
    path('opportunities/<int:pk>/', OpportunityDetailView.as_view(), name='opportunity-detail'), # retrieve, update, delete opportunity


]
