from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'engagements', views.EngagementRecordViewSet, basename='engagement')

# We use simple paths for nested tasks 
# Since I'm not sure if drf-nested-routers is installed, I will just use standard router for engagements and explicit paths for tasks, or a separate router for tasks with no prefix since it's nested under engagements.

# Let's use simple paths for nested tasks
task_list = views.TaskEntryViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
task_detail = views.TaskEntryViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # Public verification URLs
    path('verify/<uuid:id>/', views.PublicCertificateVerificationView.as_view(), name='verify-certificate'),
    path('verify/<uuid:id>/pdf/', views.DownloadCertificatePDFView.as_view(), name='download-certificate-pdf'),
    
    # Task URLs (Nested under engagements)
    path('engagements/<uuid:engagement_record_id>/tasks/', task_list, name='task-list'),
    path('engagements/<uuid:engagement_record_id>/tasks/<int:pk>/', task_detail, name='task-detail'),
    
    # DRF Router URLs for engagements
    path('', include(router.urls)),
]
