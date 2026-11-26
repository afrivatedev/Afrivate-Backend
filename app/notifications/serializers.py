from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification

MAX_MESSAGE_LENGTH = 2000


def validate_notification_link(value):
    """Allow only site-relative paths or plain http(s) URLs.

    Blocks javascript:, data:, vbscript: and protocol-relative (//host) links,
    which can run script or send the user to another site.
    """
    if not value:
        return value
    value = value.strip()
    if value.startswith('/'):
        if value.startswith('//') or value.startswith('/\\'):
            raise serializers.ValidationError('Protocol-relative links are not allowed.')
        return value
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise serializers.ValidationError('Links must start with / or http(s)://.')
    return value


class NotificationSerializer(serializers.ModelSerializer):
    current_user_read = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    # Write-only: who the notification is addressed to. Omitted/null means a
    # broadcast, which only staff are allowed to create (enforced in the view).
    recipient = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True),
        write_only=True, required=False, allow_null=True,
    )
    message = serializers.CharField(
        max_length=MAX_MESSAGE_LENGTH, required=False, allow_null=True, allow_blank=True,
    )
    link = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True,
        validators=[validate_notification_link],
    )

    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "priority", "type", "link", "created_at",
            "current_user_read", "recipient", "sender_name",
        ]
        read_only_fields = ["sender_name"]

    def get_current_user_read(self, obj):
        return getattr(obj, 'current_user_read', False)

    def get_sender_name(self, obj):
        sender = obj.sender
        if sender is None:
            return None
        return sender.get_full_name() or sender.username
