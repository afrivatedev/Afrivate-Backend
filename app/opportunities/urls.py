from django.urls import path
from .views import *

# write your urls here

urlpatterns = [
    path("health-check/", health_check, name="opportunities-health-check"),
    
    path('', OpportunityView.as_view(), name='opportunity-list'), # list and create all opportunities {post to create}, {get to list}
    
    path('mine/', EnablerOpportunityListView.as_view(), name='my-opportunities'), # list opportunities created by the logged-in enabler
    path('<int:pk>/', OpportunityDetailView.as_view(), name='opportunity-detail'), # retrieve, update, delete opportunity
    path('<int:pk>/applicants/', OpportunityApplicantListView.as_view(), name='opportunity-applicants'),
    path('<int:pk>/applicants/<int:applicant_id>/', ApplicantProfileView.as_view(), name='applicant-profile'),
]
