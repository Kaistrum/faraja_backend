from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from .models import CrisisReport, Responder, Assignment


# ==================================================
# MAP VIEW FOR ADMIN
# ==================================================
class MapView(TemplateView):
    template_name = 'admin/map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crisis Reports Map'
        context['site_header'] = 'RAPIDA Administration'
        return context


# ==================================================
# ADMIN SITE CUSTOMIZATION
# ==================================================
class CustomAdminSite(admin.AdminSite):
    site_header = "RAPIDA Administration"
    site_title = "RAPIDA Admin"
    index_title = "Welcome to RAPIDA Admin"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('map/', self.admin_view(MapView.as_view()), name='admin-map'),
        ]
        return custom_urls + urls


# Create custom admin site instance
rapida_admin = CustomAdminSite()


# ==================================================
# CRISIS REPORT ADMIN
# ==================================================
@admin.register(CrisisReport, site=rapida_admin)
class CrisisReportAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'event_id', 'damage_level', 'status', 'infrastructure_type', 'created_at']
    list_filter = ['damage_level', 'status', 'nature_of_crisis', 'infrastructure_type', 'is_verified', 'created_at']
    search_fields = ['event_name', 'event_id', 'location_text', 'description']
    readonly_fields = ['report_id', 'created_at', 'updated_at', 'ai_confidence', 'ai_description']
    
    fieldsets = (
        ('Report Identity', {
            'fields': ('report_id', 'event_id', 'event_name', 'version_number', 'is_latest', 'previous_report')
        }),
        ('Location Information', {
            'fields': ('latitude', 'longitude', 'location_text')
        }),
        ('Infrastructure Details', {
            'fields': ('infrastructure_type', 'infrastructure_name', 'affected_units')
        }),
        ('Crisis Information', {
            'fields': ('nature_of_crisis', 'damage_level', 'description', 'debris_clearing_needed')
        }),
        ('AI Analysis', {
            'fields': ('ai_damage_level', 'ai_confidence', 'ai_description'),
            'classes': ('collapse',)
        }),
        ('Submission Details', {
            'fields': ('submitter_token', 'submission_channel', 'language'),
            'classes': ('collapse',)
        }),
        ('Workflow', {
            'fields': ('status', 'is_duplicate', 'duplicate_of')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']


# ==================================================
# RESPONDER ADMIN
# ==================================================
@admin.register(Responder, site=rapida_admin)
class ResponderAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'role', 'organization', 'is_active', 'last_login']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'organization']
    readonly_fields = ['responder_id', 'created_at']
    
    fieldsets = (
        ('User Identity', {
            'fields': ('responder_id', 'name', 'email')
        }),
        ('Role & Organization', {
            'fields': ('role', 'organization')
        }),
        ('Security', {
            'fields': ('password_hash', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Activity', {
            'fields': ('last_login', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['name']


# ==================================================
# ASSIGNMENT ADMIN
# ==================================================
@admin.register(Assignment, site=rapida_admin)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['assignment_id', 'responder', 'report', 'status', 'priority', 'assigned_at', 'due_date']
    list_filter = ['status', 'priority', 'assigned_at', 'due_date']
    search_fields = ['assignment_id', 'responder__name', 'report__event_name', 'notes']
    readonly_fields = ['assignment_id', 'assigned_at']
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('assignment_id', 'report', 'responder', 'assigned_by')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'notes')
        }),
        ('Timeline', {
            'fields': ('assigned_at', 'due_date', 'completed_at')
        }),
    )
    
    ordering = ['-assigned_at']
