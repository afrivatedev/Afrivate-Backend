# # waitlist/admin.py
# from django.contrib import admin
# from django.utils.html import format_html
# from django.urls import reverse
# from django.http import HttpResponse
# import csv
# from user_database.models import WaitlistEmail           


# @admin.register(WaitlistEmail)
# class WaitlistEntryAdmin(admin.ModelAdmin):
#     list_display = ['email', 'name', 'referral_source', 'created_at']
#     list_filter = ['is_notified', 'created_at', 'referral_source']
#     search_fields = ['email', 'name']
#     readonly_fields = ['created_at']
#     date_hierarchy = 'created_at'
#     ordering = ['-created_at']
    
#     actions = ['export_to_csv', 'mark_as_notified']
    
#     fieldsets = (
#         ('Contact Information', {
#             'fields': ('email', 'name')
#         }),
#         ('Additional Details', {
#             'fields': ('referral_source')
#         }),
#         ('Metadata', {
#             'fields': ('created_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d %H:%M')
#     created_at_display.short_description = 'Joined'
#     created_at_display.admin_order_field = 'created_at'
    
#     def status_badge(self, obj):
#         # if obj.is_notified:
#         #     return format_html(
#         #         '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Notified</span>'
#         #     )
#         return format_html(
#             '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Pending</span>'
#         )
#     status_badge.short_description = 'Status'
    
#     def export_to_csv(self, request, queryset):
#         """Export selected entries to CSV"""
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="waitlist_export.csv"'
        
#         writer = csv.writer(response)
#         writer.writerow(['Email', 'Name', 'Referral Source', 'Created At'])
        
#         for entry in queryset:
#             writer.writerow([
#                 entry.email,
#                 entry.name or '',
#                 entry.referral_source or '',
#                 entry.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#                 # 'Yes' if entry.is_notified else 'No'
#             ])
        
#         return response
#     export_to_csv.short_description = "Export selected to CSV"
    
#     def mark_as_notified(self, request, queryset):
#         """Mark selected entries as notified"""
#         updated = queryset.update(is_notified=True)
#         self.message_user(request, f'{updated} entries marked as notified.')
#     mark_as_notified.short_description = "Mark selected as notified"