from django.urls import path

from organizations import views_admin as org_views_admin

from . import views_actions, views_analytics, views_auth, views_broadcasts, views_connections, views_directory

urlpatterns = [
    # Sprint 1 — admin auth (PRD 11.1)
    path('auth/login/', views_auth.AdminLoginView.as_view(), name='admin-login'),
    path('auth/refresh/', views_auth.AdminTokenRefreshView.as_view(), name='admin-refresh'),
    path('auth/me/', views_auth.AdminMeView.as_view(), name='admin-me'),

    # Sprint 2 — directory & profiles (PRD 6.1–6.2)
    path('users/', views_directory.UserDirectoryView.as_view(), name='admin-users'),
    path('users/<int:user_id>/', views_directory.UserDetailView.as_view(), name='admin-user-detail'),
    path('notes/', views_directory.AdminNotesView.as_view(), name='admin-notes'),

    # Sprint 3 — account actions (PRD 6.3)
    path('users/<int:user_id>/suspend/', views_actions.SuspendUserView.as_view(), name='admin-suspend'),
    path('users/<int:user_id>/reinstate/', views_actions.ReinstateUserView.as_view(), name='admin-reinstate'),
    path('users/<int:user_id>/edit/', views_actions.EditUserView.as_view(), name='admin-edit-user'),
    path('users/<int:user_id>/message/', views_actions.MessageUserView.as_view(), name='admin-message-user'),
    path('messages/segment/', views_actions.MessageSegmentView.as_view(), name='admin-message-segment'),
    path('actions/', views_actions.ActionLogView.as_view(), name='admin-action-log'),

    # Sprint 4 — connection oversight (PRD 6.4)
    path('connections/', views_connections.ConnectionListView.as_view(), name='admin-connections'),
    path('connections/<int:connection_id>/', views_connections.ConnectionDetailView.as_view(), name='admin-connection-detail'),

    # Sprint 5 — analytics & broadcasts (PRD 6.5–6.6)
    path('analytics/overview/', views_analytics.AnalyticsOverviewView.as_view(), name='admin-analytics'),
    path('analytics/export/', views_analytics.AnalyticsExportView.as_view(), name='admin-analytics-export'),
    path('broadcasts/', views_broadcasts.BroadcastView.as_view(), name='admin-broadcasts'),

    # Organization Verification PRD, Sprint 3 — admin review workflow.
    # Views live in organizations/views_admin.py; routed here so every
    # AdminUser-gated surface stays under one URLconf.
    path('organizations/queue/', org_views_admin.OrganizationQueueView.as_view(), name='admin-organization-queue'),
    path('organizations/<uuid:org_id>/', org_views_admin.OrganizationAdminDetailView.as_view(), name='admin-organization-detail'),
    path('organizations/<uuid:org_id>/approve/', org_views_admin.OrganizationApproveView.as_view(), name='admin-organization-approve'),
    path('organizations/<uuid:org_id>/reject/', org_views_admin.OrganizationRejectView.as_view(), name='admin-organization-reject'),
    path('organizations/<uuid:org_id>/request-info/', org_views_admin.OrganizationRequestInfoView.as_view(), name='admin-organization-request-info'),
    path('organizations/<uuid:org_id>/suspend/', org_views_admin.OrganizationSuspendView.as_view(), name='admin-organization-suspend'),
    path('organizations/<uuid:org_id>/reinstate/', org_views_admin.OrganizationReinstateView.as_view(), name='admin-organization-reinstate'),
    path('organizations/<uuid:org_id>/scuml/verify/', org_views_admin.OrganizationScumlVerifyView.as_view(), name='admin-organization-scuml-verify'),
    path('organizations/documents/<uuid:doc_id>/review/', org_views_admin.OrganizationDocumentReviewView.as_view(), name='admin-organization-document-review'),
    path('organizations/social-links/<uuid:link_id>/verify/', org_views_admin.OrganizationSocialLinkVerifyView.as_view(), name='admin-organization-social-link-verify'),
    path('organizations/representatives/queue/', org_views_admin.RepresentativeQueueView.as_view(), name='admin-representative-queue'),
    path('organizations/representatives/<uuid:rep_id>/verify/', org_views_admin.RepresentativeVerifyView.as_view(), name='admin-representative-verify'),
]
