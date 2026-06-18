from rest_framework import serializers
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry, Point as GEOSPoint
from .models import CrisisReport, Responder, Assignment, FinalCrisisReport


class GeoPointField(serializers.Field):
    """
    Accepts GeoJSON Point or [lon, lat]; serializes to GeoJSON Point.

    Input:
      {"type": "Point", "coordinates": [lon, lat]}
      or simply [lon, lat]
    Output:
      {"type": "Point", "coordinates": [lon, lat]}
    """

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = GEOSPoint(GEOSGeometry(value))
        return {"type": "Point", "coordinates": [value.x, value.y]}

    def to_internal_value(self, data):
        if isinstance(data, (list, tuple)):
            if len(data) != 2:
                raise serializers.ValidationError('Provide [longitude, latitude].')
            lon, lat = float(data[0]), float(data[1])
        elif isinstance(data, dict):
            if data.get('type') != 'Point':
                raise serializers.ValidationError('Must be a GeoJSON Point object.')
            coords = data.get('coordinates', [])
            if len(coords) != 2:
                raise serializers.ValidationError('Coordinates must be [longitude, latitude].')
            lon, lat = float(coords[0]), float(coords[1])
        else:
            raise serializers.ValidationError(
                'Use {"type": "Point", "coordinates": [lon, lat]} or [lon, lat].'
            )
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        if not (-180 <= lon <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return GEOSPoint(lon, lat, srid=4326)


# ==================================================
# CRISIS REPORT SERIALIZER
# ==================================================
class SubmitSerializer(serializers.ModelSerializer):
    location = GeoPointField(required=False, allow_null=True)

    class Meta:
        model = CrisisReport
        fields = (
            'client_id', 'location', 'location_description', 'building_footprint_id', 'infrastructure_type',
            'nature_of_crisis', 'debris', 'affected_units', 'damage_level', 'photo_url', 'submitted_at', 'raw_payload'
        )
        read_only_fields = ('raw_payload',)

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['raw_payload'] = dict(request.data)
            if not validated_data.get('submitted_at'):
                validated_data['submitted_at'] = timezone.now()
        return super().create(validated_data)


class FullSerializer(serializers.ModelSerializer):
    location = GeoPointField(required=False, allow_null=True)
    # Backwards-compatible aliases for the dashboard frontend
    event_id = serializers.SerializerMethodField()
    event_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = CrisisReport
        fields = '__all__'
        read_only_fields = ('report_id', 'created_at', 'updated_at', 'raw_payload')

    def get_event_id(self, obj):
        return str(obj.report_id)

    def get_event_name(self, obj):
        # Prefer a human-friendly description if available
        if getattr(obj, 'location_description', None):
            return obj.location_description
        if getattr(obj, 'infrastructure_type', None):
            return obj.infrastructure_type
        if getattr(obj, 'building_footprint_id', None):
            return obj.building_footprint_id
        return None

    def get_status(self, obj):
        # Best-effort mapping: unresolved if not processed, resolved if processed
        if getattr(obj, 'processed_at', None):
            return 'resolved'
        if getattr(obj, 'submitted_at', None):
            return 'pending'
        return None


class CrisisReportGeoSerializer(serializers.ModelSerializer):
    location = GeoPointField(read_only=True)
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'client_id', 'location', 'geometry', 'building_footprint_id',
            'infrastructure_type', 'nature_of_crisis', 'damage_level', 'photo_url', 'submitted_at', 'processed_at',
            'is_latest', 'ai_disaster_type', 'ai_damage_severity', 'ai_informativeness'
        )

    def get_geometry(self, obj):
        if obj.location is None:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}


class CrisisReportListSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'client_id', 'geometry', 'building_footprint_id', 'infrastructure_type',
            'nature_of_crisis', 'damage_level', 'photo_url', 'submitted_at', 'is_latest'
        )

    def get_geometry(self, obj):
        if obj.location is None:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}


# ==================================================
# RESPONDER SERIALIZER
# ==================================================
class ResponderSerializer(serializers.ModelSerializer):
    location = GeoPointField(required=False, allow_null=True)

    class Meta:
        model = Responder
        fields = "__all__"
        read_only_fields = (
            "responder_id",
            "created_at",
            "last_login"
        )
        extra_kwargs = {
            "password_hash": {"write_only": True}
        }

    def create(self, validated_data):
        return Responder.objects.create(**validated_data)


# ==================================================
# ASSIGNMENT SERIALIZER
# ==================================================
class AssignmentSerializer(serializers.ModelSerializer):

    # Extra readable fields for frontend/dashboard
    responder_name = serializers.CharField(
        source="responder.name",
        read_only=True
    )

    report_event = serializers.CharField(
        source="report.event_name",
        read_only=True
    )

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = (
            "assignment_id",
            "assigned_at",
            "completed_at"
        )

    def validate(self, data):
        """
        Business logic validation
        """

        report = data.get("report")
        responder = data.get("responder")

        if report and getattr(report, "is_duplicate", False):
            raise serializers.ValidationError("Cannot assign duplicate reports")

        if responder and not getattr(responder, "is_active", True):
            raise serializers.ValidationError("Cannot assign inactive responder")

        return data


# ==================================================
# FINAL CRISIS REPORT SERIALIZER
# ==================================================
class FinalCrisisReportSerializer(serializers.ModelSerializer):
    location = GeoPointField(required=False, allow_null=True)

    class Meta:
        model = FinalCrisisReport
        fields = '__all__'
        read_only_fields = ('report_id', 'created_at', 'updated_at', 'raw_payload')


class FinalCrisisReportListSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = FinalCrisisReport
        fields = (
            'report_id', 'client_id', 'original_report_id', 'geometry', 'building_footprint_id',
            'infrastructure_type', 'nature_of_crisis', 'damage_level', 'photo_url', 'submitted_at'
        )

    def get_geometry(self, obj):
        if obj.location is None:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}


class DuplicateCheckSerializer(serializers.Serializer):
    """Response serializer for duplicate check endpoint"""
    is_duplicate = serializers.BooleanField()
    matched_report_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField()
    report_data = FinalCrisisReportSerializer(required=False, allow_null=True)