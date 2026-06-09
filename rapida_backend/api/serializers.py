from rest_framework import serializers
from django.utils import timezone
from .models import CrisisReport, Responder, Assignment


# ==================================================
# CRISIS REPORT SERIALIZER
# ==================================================
class SubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisReport
        fields = (
            'client_id', 'lat', 'lon', 'location_description', 'building_footprint_id', 'infrastructure_type',
            'nature_of_crisis', 'debris', 'affected_units', 'damage_level', 'photo_url', 'submitted_at', 'raw_payload'
        )
        read_only_fields = ('raw_payload',)

    def validate(self, data):
        lat = data.get('lat')
        lon = data.get('lon')
        if lat is not None and (lat < -90 or lat > 90):
            raise serializers.ValidationError({'lat': 'Invalid latitude value. Must be between -90 and 90.'})
        if lon is not None and (lon < -180 or lon > 180):
            raise serializers.ValidationError({'lon': 'Invalid longitude value. Must be between -180 and 180.'})
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['raw_payload'] = dict(request.data)
            # allow submitted_at override, else set now
            if not validated_data.get('submitted_at'):
                validated_data['submitted_at'] = timezone.now()
        return super().create(validated_data)


class FullSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisReport
        fields = '__all__'
        read_only_fields = ('report_id', 'created_at', 'updated_at', 'raw_payload')


class CrisisReportGeoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'client_id', 'lat', 'lon', 'location', 'building_footprint_id',
            'infrastructure_type', 'nature_of_crisis', 'damage_level', 'photo_url', 'submitted_at', 'processed_at',
            'is_latest', 'ai_disaster_type', 'ai_damage_severity', 'ai_informativeness'
        )


class CrisisReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisReport
        fields = (
            'report_id', 'client_id', 'lat', 'lon', 'building_footprint_id', 'infrastructure_type',
            'nature_of_crisis', 'damage_level', 'photo_url', 'submitted_at', 'is_latest'
        )


# ==================================================
# RESPONDER SERIALIZER
# ==================================================
class ResponderSerializer(serializers.ModelSerializer):

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
        """
        NOTE: later replace with proper password hashing (bcrypt / Django auth)
        """
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