import uuid
from datetime import datetime

from django.db import models
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured


# ==================================================
# CRISIS REPORT
# ==================================================
class CrisisReport(models.Model):

    class DamageLevel(models.TextChoices):
        MINIMAL = 'minimal', 'Minimal'
        PARTIAL = 'partial', 'Partial'
        COMPLETE = 'complete', 'Complete'

    class AIDamageLevel(models.TextChoices):
        MINIMAL = 'minimal', 'Minimal'
        PARTIAL = 'partial', 'Partial'
        COMPLETE = 'complete', 'Complete'

    class AIDisasterType(models.TextChoices):
        EARTHQUAKE = 'earthquake', 'Earthquake'
        FIRE = 'fire', 'Fire'
        FLOOD = 'flood', 'Flood'
        HURRICANE = 'hurricane', 'Hurricane'
        LANDSLIDE = 'landslide', 'Landslide'
        NOT_DISASTER = 'not_disaster', 'Not disaster'
        OTHER = 'other_disaster', 'Other'

    class AIInformativeness(models.TextChoices):
        INFORMATIVE = 'informative', 'Informative'
        NOT_INFORMATIVE = 'not_informative', 'Not informative'

    class AIHumanitarianCategory(models.TextChoices):
        AFFECTED = 'affected_injured_or_dead_people', 'Affected/injured/dead people'
        INFRA = 'infrastructure_and_utility_damage', 'Infrastructure and utility damage'
        NOT_HUM = 'not_humanitarian', 'Not humanitarian'
        RESCUE = 'rescue_volunteering_or_donation_effort', 'Rescue/volunteering/donation effort'

    class AIDamageSeverity(models.TextChoices):
        LITTLE = 'little_or_no_damage', 'Little or no damage'
        MILD = 'mild_damage', 'Mild damage'
        SEVERE = 'severe_damage', 'Severe damage'

    # Identity
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.UUIDField(null=True, blank=True, unique=True)

    # Location
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    # Store location as GeoJSON dict: {"type": "Point", "coordinates": [lon, lat]}
    location = models.JSONField(null=True, blank=True)
    location_description = models.TextField(null=True, blank=True)

    # Linking / footprint
    building_footprint_id = models.CharField(max_length=255, null=True, blank=True)

    # Versioning
    is_latest = models.BooleanField(default=True)

    # Submission timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Infrastructure
    INFRASTRUCTURE_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('government', 'Government'),
        ('utility', 'Utility'),
        ('transport', 'Transport & Communication'),
        ('community', 'Community'),
        ('recreation', 'Public Recreation'),
        ('other', 'Other'),
    ]

    NATURE_OF_CRISIS_TYPES = [
        ('earthquake', 'Earthquake'),
        ('flood', 'Flood'),
        ('tsunami', 'Tsunami'),
        ('cyclone', 'Cyclone/Hurricane'),
        ('wildfire', 'Wildfire'),
        ('explosion', 'Explosion'),
        ('conflict', 'Conflict'),
        ('civil_unrest', 'Civil Unrest'),
        ('chemical', 'Chemical Incident'),
        ('other', 'Other'),
    ]

    infrastructure_type = models.CharField(max_length=50, choices=INFRASTRUCTURE_TYPES, null=True, blank=True)
    nature_of_crisis = models.CharField(max_length=50, choices=NATURE_OF_CRISIS_TYPES, null=True, blank=True)
    debris = models.BooleanField(default=False)

    # User-submitted
    affected_units = models.PositiveIntegerField(null=True, blank=True)
    damage_level = models.CharField(max_length=20, choices=DamageLevel.choices, null=True, blank=True)

    # Photo as URL (no file upload stored in DB)
    photo_url = models.TextField(null=True, blank=True)

    # AI-populated fields (nullable, filled by worker)
    ai_damage_level = models.CharField(max_length=32, choices=AIDamageLevel.choices, null=True, blank=True)
    ai_disaster_type = models.CharField(max_length=32, choices=AIDisasterType.choices, null=True, blank=True)
    ai_informativeness = models.CharField(max_length=32, choices=AIInformativeness.choices, null=True, blank=True)
    ai_humanitarian_category = models.CharField(max_length=64, choices=AIHumanitarianCategory.choices, null=True, blank=True)
    ai_damage_severity = models.CharField(max_length=32, choices=AIDamageSeverity.choices, null=True, blank=True)

    # Raw payload / metadata
    raw_payload = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['building_footprint_id', 'is_latest']),
            models.Index(fields=['ai_disaster_type']),
            models.Index(fields=['ai_damage_severity']),
            models.Index(fields=['-submitted_at']),
        ]

    def save(self, *args, **kwargs):
        # auto-populate point from lat/lon
        if (self.lat is not None) and (self.lon is not None):
            # store as GeoJSON
            try:
                self.location = {"type": "Point", "coordinates": [float(self.lon), float(self.lat)]}
            except Exception:
                self.location = None

        if not self.submitted_at:
            self.submitted_at = self.submitted_at or None

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.report_id)


# ==================================================
# RESPONDER
# ==================================================
class Responder(models.Model):

    ROLES = [
        ('admin', 'Admin'),
        ('field', 'Field Enumerator'),
        ('analyst', 'Analyst'),
        ('supervisor', 'Supervisor'),
    ]

    responder_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=50, choices=ROLES)
    organization = models.CharField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==================================================
# ASSIGNMENT
# ==================================================
class Assignment(models.Model):

    STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(CrisisReport, on_delete=models.CASCADE, related_name='assignments')
    responder = models.ForeignKey(Responder, on_delete=models.CASCADE, related_name='assignments')

    assigned_by = models.ForeignKey(
        Responder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments'
    )

    status = models.CharField(max_length=50, choices=STATUS, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY, default='normal')

    notes = models.TextField(null=True, blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.assignment_id} - {self.status}"