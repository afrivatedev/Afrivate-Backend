from django.contrib import admin
from .models import Feedback, KnowledgeBaseArticle, SupportChatSession, SupportChatMessage

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('subject', 'type', 'user', 'status', 'priority', 'created_at')
    list_filter = ('type', 'status', 'priority', 'created_at')
    search_fields = ('subject', 'description', 'user__email')

@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'last_reviewed')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description', 'solution')

class SupportChatMessageInline(admin.TabularInline):
    model = SupportChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'attachment', 'timestamp')

@admin.register(SupportChatSession)
class SupportChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email',)
    inlines = [SupportChatMessageInline]

@admin.register(SupportChatMessage)
class SupportChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'timestamp')
    list_filter = ('role', 'timestamp')
    search_fields = ('content', 'session__user__email')
