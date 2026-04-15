from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    current_user_read = serializers.SerializerMethodField()


    class Meta:
        model = Notification
        fields = ["id", "title", "message", "priority", "type", "link", "created_at", "current_user_read"]

    def get_current_user_read(self, obj):
        return getattr(obj, 'current_user_read', False)