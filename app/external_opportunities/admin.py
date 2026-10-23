from django.contrib import admin

from .models import ExternalOpportunity


@admin.register(ExternalOpportunity)
class ExternalOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'opportunity_type', 'organization_name', 'field', 'is_active', 'deadline')
    list_filter = ('source', 'opportunity_type', 'field', 'is_active', 'is_remote')
    search_fields = ('title', 'organization_name')
