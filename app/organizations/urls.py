from django.urls import path

from .views import (
    OrganizationCreateView,
    MyOrganizationsView,
    OrganizationDetailView,
    OrganizationDocumentListCreateView,
    OrganizationDocumentDeleteView,
    OrganizationSocialLinkListCreateView,
    OrganizationSocialLinkDetailView,
    OrganizationRepresentativeListCreateView,
    OrganizationRepresentativeRevokeView,
    OrganizationVouchCreateView,
    MyRepresentativeApplicationsView,
)

urlpatterns = [
    path('', OrganizationCreateView.as_view(), name='organization-create'),
    path('mine/', MyOrganizationsView.as_view(), name='organization-mine'),
    path('representatives/me/', MyRepresentativeApplicationsView.as_view(), name='organization-representative-me'),

    path('documents/<uuid:doc_id>/', OrganizationDocumentDeleteView.as_view(), name='organization-document-delete'),
    path('social-links/<uuid:link_id>/', OrganizationSocialLinkDetailView.as_view(), name='organization-social-link-detail'),

    path('<uuid:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('<uuid:org_id>/documents/', OrganizationDocumentListCreateView.as_view(), name='organization-document-list-create'),
    path('<uuid:org_id>/social-links/', OrganizationSocialLinkListCreateView.as_view(), name='organization-social-link-list-create'),
    path('<uuid:org_id>/representatives/', OrganizationRepresentativeListCreateView.as_view(), name='organization-representative-list-create'),
    path('<uuid:org_id>/representatives/<uuid:rep_id>/', OrganizationRepresentativeRevokeView.as_view(), name='organization-representative-revoke'),
    path('<uuid:org_id>/vouches/', OrganizationVouchCreateView.as_view(), name='organization-vouch-create'),
]
