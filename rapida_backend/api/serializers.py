from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import GEOSGeometry, Point as GEOSPoint
from .models import CrisisReport, Responder, Assignment, FinalCrisisReport


class GeoPointField(serializers.Field):
    """
    Read:  returns {"type": "Point", "coordinates": [lon, lat]}
    Write: accepts {"type":"Point","coordinates":[lon,lat]} or [lon, lat]
    """

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = GEOSGeometry(value)
        return {"type": "Point", "coordinates": [value.x, value.y]}

    def to_internal_value(self, data):
        if isinstance(data, (list, tuple)):
            if len(data) != 2:
                raise serializers.ValidationError('Provide [longitude, latitude].')
            lon, lat = float(data[0]), float(data[1])
        elif isinstance(data, dict):
            if data.get('type') != 'Point':
                raise serializers.ValidationError('Must be a GeoJSON Point.')
            coords = data.get('coordinates', [])
            if len(coords) != 2:
                raise serializers.ValidationError('Coordinates must be [longitude, latitude].')
            lon, lat = float(coords[0]), float(coords[1])
        else:
            raise serializers.ValidationError(
                'Use {"type":"Point","coordinates":[lon,lat]} or [lon, lat].'
            )
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        if not (-180 <= lon <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return GEOSPoint(lon, lat, srid=4326)


# ==================================================
# CRISIS REPORT
# ==================================================
class SubmitSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True, required=False, allow_null=True, help_text="Latitude (-90 to 90)")
    lon = serializers.FloatField(write_only=True, required=False, allow_null=True, help_text="Longitude (-180 to 180)")
    location = GeoPointField(required=False, allow_null=True)

    class Meta:
        model = CrisisReport
        fields = (
            'client_id', 'lat', 'lon', 'location', 'location_description',
            'building_footprint_id', 'infrastructure_type', 'nature_of_crisis',
            'debris', 'affected_units', 'damage_level', 'photo_url', 'submitted_at',
        )

    def validate(self, data):
        lat = data.pop('lat', None)
        lon = data.pop('lon', None)
        if lat is not None and lon is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError({'lat': 'Must be between -90 and 90.'})
            if not (-180 <= lon <= 180):
                raise serializers.ValidationError({'lon': 'Must be between -180 and 180.'})
            data['location'] = GEOSPoint(lon, lat, srid=4326)
        return data

    def create(self, validated_data):
        if not validated_data.get('submitted_at'):
            validated_data['submitted_at'] = timezone.now()
        return super().create(validated_data)


class FullSerializer(serializers.ModelSerializer):
    location = GeoPointField(read_only=True)
    lat = serializers.SerializerMethodField()
    lon = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'client_id', 'lat', 'lon', 'location', 'location_description',
            'building_footprint_id', 'is_latest', 'infrastructure_type', 'nature_of_crisis',
            'debris', 'affected_units', 'damage_level', 'photo_url',
            'submitted_at', 'processed_at', 'status',
            'ai_disaster_type', 'ai_damage_level', 'ai_damage_severity',
            'ai_informativeness', 'ai_humanitarian_category',
            'created_at', 'updated_at',
        )

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lon(self, obj):
        return obj.location.x if obj.location else None

    def get_status(self, obj):
        if obj.processed_at:
            return 'resolved'
        if obj.submitted_at:
            return 'pending'
        return None


class CrisisReportListSerializer(serializers.ModelSerializer):
    location = GeoPointField(read_only=True)
    lat = serializers.SerializerMethodField()
    lon = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'lat', 'lon', 'location', 'building_footprint_id',
            'infrastructure_type', 'nature_of_crisis', 'damage_level',
            'submitted_at', 'status', 'is_latest',
            'ai_disaster_type', 'ai_damage_severity',
        )

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lon(self, obj):
        return obj.location.x if obj.location else None

    def get_status(self, obj):
        if obj.processed_at:
            return 'resolved'
        if obj.submitted_at:
            return 'pending'
        return None


# ==================================================
# RESPONDER
# ==================================================
class ResponderSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True, required=False, allow_null=True, help_text="Latitude (-90 to 90)")
    lon = serializers.FloatField(write_only=True, required=False, allow_null=True, help_text="Longitude (-180 to 180)")
    location = GeoPointField(required=False, allow_null=True)

    class Meta:
        model = Responder
        fields = '__all__'
        read_only_fields = ('responder_id', 'created_at', 'last_login')
        extra_kwargs = {'password_hash': {'write_only': True}}

    def validate(self, data):
        lat = data.pop('lat', None)
        lon = data.pop('lon', None)
        if lat is not None and lon is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError({'lat': 'Must be between -90 and 90.'})
            if not (-180 <= lon <= 180):
                raise serializers.ValidationError({'lon': 'Must be between -180 and 180.'})
            data['location'] = GEOSPoint(lon, lat, srid=4326)
        return data

    def create(self, validated_data):
        validated_data['password_hash'] = make_password(validated_data['password_hash'])
        return Responder.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if 'password_hash' in validated_data:
            validated_data['password_hash'] = make_password(validated_data['password_hash'])
        return super().update(instance, validated_data)


# ==================================================
# ASSIGNMENT
# ==================================================
class AssignmentSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.name', read_only=True)

    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ('assignment_id', 'assigned_at', 'completed_at')

    def validate(self, data):
        if data.get('responder') and not data['responder'].is_active:
            raise serializers.ValidationError('Cannot assign an inactive responder.')
        return data


# ==================================================
# FINAL CRISIS REPORT
# ==================================================
class FinalCrisisReportSerializer(serializers.ModelSerializer):
    location = GeoPointField(read_only=True)
    lat = serializers.SerializerMethodField()
    lon = serializers.SerializerMethodField()

    class Meta:
        model = FinalCrisisReport
        fields = (
            'report_id', 'original_report_id', 'client_id',
            'lat', 'lon', 'location', 'location_description',
            'building_footprint_id', 'infrastructure_type', 'nature_of_crisis',
            'debris', 'affected_units', 'damage_level', 'photo_url',
            'submitted_at', 'processed_at',
            'ai_disaster_type', 'ai_damage_level', 'ai_damage_severity',
            'ai_informativeness', 'ai_humanitarian_category',
            'created_at', 'updated_at',
        )

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lon(self, obj):
        return obj.location.x if obj.location else None


class FinalCrisisReportListSerializer(serializers.ModelSerializer):
    location = GeoPointField(read_only=True)
    lat = serializers.SerializerMethodField()
    lon = serializers.SerializerMethodField()

    class Meta:
        model = FinalCrisisReport
        fields = (
            'report_id', 'original_report_id', 'lat', 'lon', 'location',
            'building_footprint_id', 'infrastructure_type', 'nature_of_crisis',
            'damage_level', 'submitted_at',
            'ai_disaster_type', 'ai_damage_severity',
        )

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lon(self, obj):
        return obj.location.x if obj.location else None
