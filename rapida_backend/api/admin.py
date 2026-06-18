from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django import forms
from .models import CrisisReport, Responder, Assignment, FinalCrisisReport
from .widgets import LocationMapWidget


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
    list_display = ['report_id', 'building_footprint_id', 'infrastructure_type', 'nature_of_crisis', 'damage_level', 'is_latest', 'submitted_at']
    list_filter = ['damage_level', 'infrastructure_type', 'nature_of_crisis', 'is_latest', 'submitted_at']
    search_fields = ['report_id', 'building_footprint_id', 'photo_url']
    readonly_fields = ['report_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Report Identity', {
            'fields': ('report_id', 'client_id', 'is_latest')
        }),
        ('Location Information', {
            'fields': ('location', 'location_description', 'building_footprint_id')
        }),
        ('Infrastructure Details', {
            'fields': ('infrastructure_type', 'nature_of_crisis', 'affected_units', 'debris')
        }),
        ('User Assessment', {
            'fields': ('damage_level', 'photo_url')
        }),
        ('AI Analysis', {
            'fields': ('ai_damage_level', 'ai_disaster_type', 'ai_informativeness', 'ai_humanitarian_category', 'ai_damage_severity'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'processed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-submitted_at']


# ==================================================
# FINAL CRISIS REPORT ADMIN (Dashboard/Verified)
# ==================================================
@admin.register(FinalCrisisReport, site=rapida_admin)
class FinalCrisisReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'original_report_id', 'building_footprint_id', 'infrastructure_type', 'nature_of_crisis', 'damage_level', 'submitted_at']
    list_filter = ['damage_level', 'infrastructure_type', 'nature_of_crisis', 'ai_disaster_type', 'submitted_at']
    search_fields = ['report_id', 'building_footprint_id', 'original_report_id']
    readonly_fields = ['report_id', 'original_report_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Report Identity', {
            'fields': ('report_id', 'original_report_id', 'client_id')
        }),
        ('Location Information', {
            'fields': ('location', 'location_description', 'building_footprint_id')
        }),
        ('Infrastructure Details', {
            'fields': ('infrastructure_type', 'nature_of_crisis', 'affected_units', 'debris')
        }),
        ('User Assessment', {
            'fields': ('damage_level', 'photo_url')
        }),
        ('AI Analysis', {
            'fields': ('ai_damage_level', 'ai_disaster_type', 'ai_informativeness', 'ai_humanitarian_category', 'ai_damage_severity'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'processed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-submitted_at']


# ==================================================
class ResponderForm(forms.ModelForm):
    """Custom form for Responder with map widget for location"""
    location = forms.CharField(
        widget=LocationMapWidget(),
        required=False,
        help_text="Click on the map to set your current location"
    )
    
    class Meta:
        model = Responder
        fields = ['name', 'email', 'password_hash', 'role', 'organization', 'location', 'location_description', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.location:
            import json
            pt = self.instance.location
            self.fields['location'].initial = json.dumps(
                {"type": "Point", "coordinates": [pt.x, pt.y]}
            )

    def clean(self):
        import json
        from django.contrib.gis.geos import Point as GEOSPoint
        cleaned_data = super().clean()
        location = cleaned_data.get('location')
        if location:
            try:
                if isinstance(location, str):
                    data = json.loads(location)
                    if data.get('type') != 'Point':
                        raise forms.ValidationError('Must be a GeoJSON Point.')
                    coords = data.get('coordinates', [])
                    if len(coords) != 2:
                        raise forms.ValidationError('Coordinates must be [longitude, latitude].')
                    cleaned_data['location'] = GEOSPoint(coords[0], coords[1], srid=4326)
            except (json.JSONDecodeError, ValueError):
                raise forms.ValidationError('Invalid location format. Must be valid GeoJSON.')
        return cleaned_data


@admin.register(Responder, site=rapida_admin)
class ResponderAdmin(admin.ModelAdmin):
    form = ResponderForm
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
        ('Current Location', {
            'fields': ('location', 'location_description'),
            'description': 'Set your current location using the map. Click on the map to mark your position.'
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
