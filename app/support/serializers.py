from rest_framework import serializers
from .models import Feedback, KnowledgeBaseArticle, SupportChatSession, SupportChatMessage

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'type', 'rating', 'subject', 'description', 'attachment', 'context_info', 'status', 'priority', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'status', 'priority', 'created_at', 'updated_at']

class KnowledgeBaseArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBaseArticle
        fields = '__all__'

class SupportChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportChatMessage
        fields = ['id', 'session', 'role', 'content', 'attachment', 'timestamp']
        read_only_fields = ['id', 'session', 'role', 'timestamp']

class SupportChatSessionSerializer(serializers.ModelSerializer):
    messages = SupportChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportChatSession
        fields = ['id', 'user', 'status', 'escalated_ticket', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'user', 'status', 'escalated_ticket', 'created_at', 'updated_at']
