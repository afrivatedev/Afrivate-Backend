from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeedbackViewSet, SupportChatSessionViewSet

router = DefaultRouter()
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'chat/sessions', SupportChatSessionViewSet, basename='chat-sessions')

urlpatterns = [
    path('', include(router.urls)),
]
