import uuid
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt

from django.contrib.gis.db import models
from django.utils import timezone


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
    location = models.PointField(null=True, blank=True, srid=4326)
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

    location = models.PointField(null=True, blank=True, srid=4326)
    location_description = models.TextField(null=True, blank=True, help_text="Human-readable location description")

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


# ==================================================
# UTILITY FUNCTIONS
# ==================================================
def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate distance between two geographic points in meters using Haversine formula.
    Coordinates: (longitude, latitude)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


def is_duplicate_report(crisis_report, threshold_distance_meters=50, threshold_hours=48):
    """
    Check if a CrisisReport is a duplicate of existing FinalCrisisReports.
    
    Duplicate logic:
    1. If building_footprint_id matches -> DUPLICATE
    2. If location within threshold_distance + same infrastructure_type + within threshold_hours -> DUPLICATE
    
    Returns: (is_duplicate: bool, matched_report_id: UUID or None, reason: str)
    """
    if not crisis_report.submitted_at:
        return False, None, "No submitted_at timestamp"
    
    # Check 1: Same building footprint
    if crisis_report.building_footprint_id:
        existing = FinalCrisisReport.objects.filter(
            building_footprint_id=crisis_report.building_footprint_id
        ).first()
        if existing:
            return True, existing.report_id, "Duplicate: same building_footprint_id"
    
    # Check 2: Spatial + Temporal + Infrastructure match
    if crisis_report.location and crisis_report.infrastructure_type:
        lon, lat = crisis_report.location.x, crisis_report.location.y
        time_window_start = crisis_report.submitted_at - timedelta(hours=threshold_hours)
        time_window_end = crisis_report.submitted_at + timedelta(hours=threshold_hours)

        candidates = FinalCrisisReport.objects.filter(
            infrastructure_type=crisis_report.infrastructure_type,
            submitted_at__gte=time_window_start,
            submitted_at__lte=time_window_end
        )

        for candidate in candidates:
            if candidate.location:
                c_lon, c_lat = candidate.location.x, candidate.location.y
                distance = haversine_distance(lon, lat, c_lon, c_lat)
                if distance <= threshold_distance_meters:
                    return True, candidate.report_id, f"Duplicate: within {threshold_distance_meters}m, same infrastructure, within {threshold_hours}h"
    
    return False, None, "No duplicate found"


def get_nearest_responders(location_coords, max_distance_meters=5000, limit=5):
    """
    Find responders closest to a given location.

    Args:
        location_coords: [longitude, latitude] list/tuple
        max_distance_meters: Maximum search radius
        limit: Maximum number of responders to return

    Returns: List of (responder, distance_meters) tuples, sorted by distance
    """
    responders_with_distances = []
    lon, lat = location_coords[0], location_coords[1]

    for responder in Responder.objects.filter(is_active=True, location__isnull=False):
        r_lon, r_lat = responder.location.x, responder.location.y
        distance = haversine_distance(lon, lat, r_lon, r_lat)
        if distance <= max_distance_meters:
            responders_with_distances.append((responder, distance))

    responders_with_distances.sort(key=lambda x: x[1])
    return responders_with_distances[:limit]


# ==================================================
# FINAL CRISIS REPORT (for dashboards)
# ==================================================
class FinalCrisisReport(models.Model):

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
    client_id = models.UUIDField(null=True, blank=True)
    original_report_id = models.UUIDField(null=True, blank=True, help_text="Reference to source CrisisReport")

    # Location
    location = models.PointField(null=True, blank=True, srid=4326)
    location_description = models.TextField(null=True, blank=True)

    # Linking / footprint
    building_footprint_id = models.CharField(max_length=255, null=True, blank=True)

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

    # Photo as URL
    photo_url = models.TextField(null=True, blank=True)

    # AI-populated fields
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
            models.Index(fields=['building_footprint_id']),
            models.Index(fields=['infrastructure_type']),
            models.Index(fields=['ai_disaster_type']),
            models.Index(fields=['-submitted_at']),
        ]

    def __str__(self):
        return str(self.report_id)