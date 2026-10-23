from django.urls import path

from .views import ExternalOpportunityDetailView, ExternalOpportunityListView

urlpatterns = [
    path('', ExternalOpportunityListView.as_view(), name='external-opportunity-list'),
    path('<int:pk>/', ExternalOpportunityDetailView.as_view(), name='external-opportunity-detail'),
]
