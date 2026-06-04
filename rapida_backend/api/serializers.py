from rest_framework import serializers
from .models import CrisisReport, Responder, Assignment


# ==================================================
# CRISIS REPORT SERIALIZER
# ==================================================
class CrisisReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = CrisisReport
        fields = "__all__"
        read_only_fields = (
            "report_id",
            "created_at",
            "updated_at",
            "is_latest",
            "raw_payload"
        )

    def validate(self, data):
        """
        Validation logic for crisis report
        """
        
        # Validate coordinates if provided
        lat = data.get("latitude")
        lon = data.get("longitude")

        if lat is not None and (lat < -90 or lat > 90):
            raise serializers.ValidationError({"latitude": "Invalid latitude value. Must be between -90 and 90."})

        if lon is not None and (lon < -180 or lon > 180):
            raise serializers.ValidationError({"longitude": "Invalid longitude value. Must be between -180 and 180."})

        # Ensure required fields have values
        if not data.get("event_name"):
            raise serializers.ValidationError({"event_name": "Event name is required."})
        
        if not data.get("event_id"):
            raise serializers.ValidationError({"event_id": "Event ID is required."})

        if not data.get("infrastructure_type"):
            raise serializers.ValidationError({"infrastructure_type": "Infrastructure type is required."})

        if not data.get("nature_of_crisis"):
            raise serializers.ValidationError({"nature_of_crisis": "Nature of crisis is required."})

        if not data.get("damage_level"):
            raise serializers.ValidationError({"damage_level": "Damage level is required."})

        return data

    def create(self, validated_data):
        """
        Capture full survey/raw request payload
        """
        try:
            request = self.context.get("request")

            if request:
                validated_data["raw_payload"] = dict(request.data)

            return super().create(validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating report: {str(e)}")


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