import uuid
from django.db import models


# ==================================================
# CRISIS REPORT
# ==================================================
class CrisisReport(models.Model):

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

    NATURE_OF_CRISIS = [
        ('earthquake', 'Earthquake'),
        ('flood', 'Flood'),
        ('tsunami', 'Tsunami'),
        ('cyclone', 'Cyclone/Hurricane'),
        ('wildfire', 'Wildfire'),
        ('explosion', 'Explosion'),
        ('conflict', 'Conflict'),
        ('civil_unrest', 'Civil Unrest'),
        ('chemical', 'Chemical Incident'),
    ]

    DAMAGE_LEVELS = [
        ('minimal', 'Minimal'),
        ('partial', 'Partial'),
        ('complete', 'Complete'),
    ]

    STATUS = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    SUBMISSION_CHANNELS = [
        ('web', 'Web'),
        ('mobile', 'Mobile'),
        ('whatsapp', 'WhatsApp'),
        ('offline', 'Offline'),
    ]

    LANGUAGES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('ar', 'Arabic'),
        ('ru', 'Russian'),
        ('zh', 'Chinese'),
    ]

    # Identity
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=100)
    event_name = models.CharField(max_length=255)

    # Versioning
    version_number = models.IntegerField(default=1)
    is_latest = models.BooleanField(default=True)

    previous_report = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions"
    )

    # Location
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_text = models.TextField(null=True, blank=True)

    # Infrastructure
    infrastructure_type = models.CharField(max_length=50, choices=INFRASTRUCTURE_TYPES)
    infrastructure_name = models.CharField(max_length=255, null=True, blank=True)
    affected_units = models.IntegerField(default=1)

    # Crisis
    nature_of_crisis = models.CharField(max_length=50, choices=NATURE_OF_CRISIS)
    damage_level = models.CharField(max_length=20, choices=DAMAGE_LEVELS)
    description = models.TextField(null=True, blank=True)
    debris_clearing_needed = models.BooleanField(default=False)

    # Media
    photos = models.JSONField(default=list, blank=True)

    # AI fields
    ai_damage_level = models.CharField(max_length=50, null=True, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_description = models.TextField(null=True, blank=True)

    # Submission
    submitter_token = models.CharField(max_length=255, null=True, blank=True)
    submission_channel = models.CharField(max_length=50, choices=SUBMISSION_CHANNELS, null=True, blank=True)
    language = models.CharField(max_length=10, choices=LANGUAGES, default='en')

    # Workflow
    status = models.CharField(max_length=50, choices=STATUS, default='pending')

    raw_payload = models.JSONField(default=dict, blank=True)
    # Duplicate detection
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="duplicates"
    )

    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Custom AI responses
    custom_responses = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_name} - {self.damage_level}"


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