from django.urls import path
from .views import WaitlistEmailView, WaitlistStatsView

app_name = "waitlist"

urlpatterns = [
    path('', WaitlistEmailView.as_view(), name='waitlist-index'),
    path('stats/', WaitlistStatsView.as_view(), name='waitlist-stats'),
]