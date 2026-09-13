from django.contrib import admin

from .models import (
    Organization,
    OrganizationDocument,
    OrganizationSocialLink,
    OrganizationRepresentative,
    OrganizationVouch,
    VerificationAuditLog,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization_type', 'tier', 'tier_status', 'created_by', 'created_at')
    list_filter = ('tier', 'tier_status', 'organization_type')
    search_fields = ('name', 'registry_id', 'scuml_id')


@admin.register(OrganizationDocument)
class OrganizationDocumentAdmin(admin.ModelAdmin):
    list_display = ('organization', 'document_type', 'review_status', 'uploaded_at')
    list_filter = ('document_type', 'review_status')


@admin.register(OrganizationSocialLink)
class OrganizationSocialLinkAdmin(admin.ModelAdmin):
    list_display = ('organization', 'platform', 'url', 'activity_verified')
    list_filter = ('platform', 'activity_verified')


@admin.register(OrganizationRepresentative)
class OrganizationRepresentativeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'organization', 'verification_status', 'created_at')
    list_filter = ('verification_status',)
    search_fields = ('full_name', 'work_email', 'phone_number')


@admin.register(OrganizationVouch)
class OrganizationVouchAdmin(admin.ModelAdmin):
    list_display = ('from_organization', 'to_organization', 'created_by', 'created_at')
    search_fields = ('from_organization__name', 'to_organization__name')


@admin.register(VerificationAuditLog)
class VerificationAuditLogAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'entity_id', 'action', 'performed_by_admin', 'created_at')
    list_filter = ('entity_type', 'action')
