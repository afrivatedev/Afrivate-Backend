from django.contrib import admin
from .models import Opportunity

# Register your models here.

admin.site.site_header = "Afrivate Admin"
admin.site.site_title = "Afrivate Admin Portal"
admin.site.index_title = "Welcome to the Afrivate Admin Portal"


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'opportunity_type', 'organization_name', 'source', 'field', 'is_open', 'deadline', 'posted_at')
    list_filter = ('opportunity_type', 'source', 'field', 'is_open', 'is_remote')
    search_fields = ('title', 'organization_name')
