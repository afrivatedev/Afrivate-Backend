from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination

from .models import ExternalOpportunity
from .serializers import ExternalOpportunitySerializer


class ExternalOpportunityPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ExternalOpportunityListView(ListAPIView):
    """GET /api/external-opportunities/?field=tech&opportunity_type=internship&search=python — active scraped listings."""
    serializer_class = ExternalOpportunitySerializer
    pagination_class = ExternalOpportunityPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['field', 'opportunity_type', 'source', 'is_remote']
    search_fields = ['title', 'organization_name', 'description']
    ordering_fields = ['posted_at', 'deadline']

    def get_queryset(self):
        return ExternalOpportunity.objects.filter(is_active=True)


class ExternalOpportunityDetailView(RetrieveAPIView):
    serializer_class = ExternalOpportunitySerializer

    def get_queryset(self):
        return ExternalOpportunity.objects.filter(is_active=True)
