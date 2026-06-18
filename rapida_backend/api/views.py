from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from datetime import timedelta

from django_filters.rest_framework import DjangoFilterBackend

from .models import CrisisReport, Responder, Assignment, FinalCrisisReport, is_duplicate_report
from .serializers import (
    SubmitSerializer,
    FullSerializer,
    CrisisReportGeoSerializer,
    CrisisReportListSerializer,
    ResponderSerializer,
    AssignmentSerializer,
    FinalCrisisReportSerializer,
    FinalCrisisReportListSerializer,
    DuplicateCheckSerializer,
)


# ==================================================
# LANDING PAGE
# ==================================================
class LandingPageView(APIView):
    """Landing page showing all available endpoints"""
    
    def get(self, request):
        host = request.get_host()
        base = f"http://{host}"
        return Response({
            "title": "RAPIDA API",
            "description": "UNDP Crisis Damage Assessment API",
            "version": "1.0.0",
            "endpoints": {
                "documentation": {
                    "Swagger UI": f"{base}/api/schema/swagger-ui/",
                    "ReDoc": f"{base}/api/schema/redoc/",
                    "OpenAPI JSON": f"{base}/api/schema/",
                },
                "visualization": {
                    "Crisis Map (web)": f"{base}/map/",
                },
                "api": {
                    "Crisis Reports (collection)": f"{base}/api/reports/",
                    "Crisis Reports (detail)": f"{base}/api/reports/{'{report_id}'}/",
                    "Reports Stats": f"{base}/api/reports/stats/",
                    "Reports by footprint": f"{base}/api/reports/by_footprint/?building_footprint_id={{id}}",
                    "AI patch (per report)": f"{base}/api/reports/{{report_id}}/ai-fill/",
                    "Check duplicate status": f"{base}/api/reports/{{report_id}}/duplicate-check/",
                    "Final Reports (dashboard)": f"{base}/api/final-reports/",
                    "Final Reports (detail)": f"{base}/api/final-reports/{'{report_id}'}/",
                    "Final Reports Stats": f"{base}/api/final-reports/stats/",
                    "Final Reports by footprint": f"{base}/api/final-reports/by_footprint/?building_footprint_id={{id}}",
                    "Final Reports GeoJSON": f"{base}/api/final-reports/geometry/",
                    "Responders": f"{base}/api/responders/",
                    "Responders (nearest)": f"{base}/api/responders/nearest/?lon={{longitude}}&lat={{latitude}}&max_distance={{meters}}&limit={{count}}",
                    "Assignments": f"{base}/api/assignments/",
                },
                "admin": {
                    "Admin Panel": f"{base}/admin/",
                }
            },
            "workflow": {
                "description": "Automatic CrisisReport Processing Workflow",
                "steps": [
                    "1. POST /api/reports/ - Submit a new CrisisReport",
                    "2. [AUTOMATIC] Check for duplicates (signal handler triggered)",
                    "   - Option A: If duplicate (same building OR coordinates<50m + same infrastructure + <48h) → No FinalCrisisReport created",
                    "   - Option B: If NOT duplicate → Automatically creates FinalCrisisReport",
                    "3. GET /api/reports/{report_id}/duplicate-check/ - Check duplicate status",
                    "4. GET /api/final-reports/ - Fetch all verified reports for dashboards"
                ],
                "notes": [
                    "FinalCrisisReports are the source of truth for dashboards",
                    "Only non-duplicate CrisisReports generate FinalCrisisReports",
                    "Duplicate detection happens automatically via Django signals",
                ]
            },
            "schemas": {
                "CrisisReport": {
                    "report_id": "UUID (primary key)",
                    "client_id": "UUID (optional, unique)",
                    "location": "JSON (GeoJSON Point) - {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "Text - human readable location",
                    "building_footprint_id": "String - external footprint id",
                    "is_latest": "Boolean - versioning flag",
                    "submitted_at": "DateTime (nullable)",
                    "processed_at": "DateTime (nullable)",
                    "infrastructure_type": "Enum - infrastructure category",
                    "nature_of_crisis": "Enum - crisis type",
                    "debris": "Boolean",
                    "affected_units": "Integer (nullable)",
                    "damage_level": "Enum - minimal/partial/complete",
                    "photo_url": "Text (URL)",
                    "ai_damage_level": "Enum (nullable)",
                    "ai_disaster_type": "Enum (nullable)",
                    "ai_informativeness": "Enum (nullable)",
                    "ai_humanitarian_category": "Enum (nullable)",
                    "ai_damage_severity": "Enum (nullable)",
                    "raw_payload": "JSON - original submission payload",
                    "created_at": "DateTime",
                    "updated_at": "DateTime",
                },
                "FinalCrisisReport": {
                    "description": "Verified, non-duplicate CrisisReport for dashboards",
                    "report_id": "UUID (primary key)",
                    "original_report_id": "UUID - reference to source CrisisReport",
                    "client_id": "UUID (optional)",
                    "location": "JSON (GeoJSON Point) - {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "Text - human readable location",
                    "building_footprint_id": "String - external footprint id",
                    "submitted_at": "DateTime (nullable)",
                    "processed_at": "DateTime (nullable)",
                    "infrastructure_type": "Enum - infrastructure category",
                    "nature_of_crisis": "Enum - crisis type",
                    "debris": "Boolean",
                    "affected_units": "Integer (nullable)",
                    "damage_level": "Enum - minimal/partial/complete",
                    "photo_url": "Text (URL)",
                    "ai_damage_level": "Enum (nullable)",
                    "ai_disaster_type": "Enum (nullable)",
                    "ai_informativeness": "Enum (nullable)",
                    "ai_humanitarian_category": "Enum (nullable)",
                    "ai_damage_severity": "Enum (nullable)",
                    "raw_payload": "JSON - original submission payload",
                    "created_at": "DateTime",
                    "updated_at": "DateTime"
                },
                "Responder": {
                    "responder_id": "UUID (primary key)",
                    "name": "String",
                    "email": "Email (unique)",
                    "password_hash": "String (write-only)",
                    "role": "Enum - admin/field/analyst/supervisor",
                    "organization": "String (optional)",
                    "is_active": "Boolean",
                    "location": "JSON (GeoJSON Point) - responder's current location {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "Text - human-readable location description",
                    "last_login": "DateTime (nullable)",
                    "created_at": "DateTime"
                }
            },
            "notes": [
                "POST /api/reports/ accepts: client_id, location (GeoJSON), location_description, building_footprint_id, infrastructure_type, nature_of_crisis, debris, affected_units, damage_level, photo_url, submitted_at",
                "Duplicate detection is AUTOMATIC via Django signals",
                "Use /api/final-reports/ for dashboard data (already verified non-duplicates)",
                "Use /api/reports/ for raw submissions (includes potential duplicates)",
                "Responders must have location set for assignment optimization",
                "GET /api/responders/nearest/?lon=X&lat=Y&max_distance=5000&limit=5 finds closest responders",
            ],
            "message": "This endpoint documents available routes, schemas, and automatic CrisisReport processing workflow."
        })


# ==================================================
# CRISIS REPORT API
# ==================================================
class CrisisReportViewSet(viewsets.ModelViewSet):
    queryset = CrisisReport.objects.all()
    serializer_class = FullSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ai_disaster_type', 'ai_damage_severity', 'ai_informativeness', 'building_footprint_id', 'nature_of_crisis']
    search_fields = ['building_footprint_id', 'infrastructure_type', 'damage_level', 'nature_of_crisis']
    ordering_fields = ['submitted_at', 'damage_level']

    def get_queryset(self):
        return CrisisReport.objects.filter(is_latest=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return SubmitSerializer
        return FullSerializer

    def create(self, request, *args, **kwargs):
        """Handle duplicates and building footprint versioning"""
        try:
            data = request.data

            # quick duplicate by client_id
            client_id = data.get('client_id')
            if client_id:
                existing = CrisisReport.objects.filter(client_id=client_id).first()
                if existing:
                    serializer = FullSerializer(existing, context={'request': request})
                    return Response(serializer.data, status=200)

            # photo+lat+lon duplicate within 60s
            photo_url = data.get('photo_url')
            lat = data.get('lat')
            lon = data.get('lon')
            if photo_url and lat is not None and lon is not None:
                cutoff = timezone.now() - timedelta(seconds=60)
                dup_qs = CrisisReport.objects.filter(photo_url=photo_url, lat=lat, lon=lon, submitted_at__gte=cutoff)
                if dup_qs.exists():
                    return Response({'detail': 'Duplicate recent report'}, status=status.HTTP_409_CONFLICT)

            # proceed with normal create
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # building footprint handling: mark previous as not latest
            bf = getattr(instance, 'building_footprint_id', None)
            if bf:
                previous = CrisisReport.objects.filter(building_footprint_id=bf, is_latest=True).exclude(report_id=instance.report_id).first()
                if previous:
                    previous.is_latest = False
                    previous.save()
                    instance.is_latest = True
                    instance.save()

            out_serializer = FullSerializer(instance, context={'request': request})
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {
                    "error": str(e),
                    "detail": "An error occurred while creating the crisis report. Please check all required fields are provided."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            "total": CrisisReport.objects.count(),
            "with_ai": CrisisReport.objects.exclude(ai_disaster_type__isnull=True).count(),
            "critical": CrisisReport.objects.filter(damage_level="complete").count(),
        })

    @action(detail=False, methods=['get'])
    def by_footprint(self, request):
        bf = request.query_params.get('building_footprint_id')
        qs = CrisisReport.objects.filter(building_footprint_id=bf)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='ai-fill')
    def ai_fill(self, request, pk=None):
        """Patch AI-populated fields and set processed_at to now"""
        instance = self.get_object()
        allowed = ['ai_damage_level', 'ai_disaster_type', 'ai_informativeness', 'ai_humanitarian_category', 'ai_damage_severity']
        updated = False
        for k in allowed:
            if k in request.data:
                setattr(instance, k, request.data.get(k))
                updated = True

        # processed_at override allowed, but set to now if not provided
        instance.processed_at = timezone.now()
        instance.save()
        serializer = FullSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='duplicate-check')
    def duplicate_check(self, request, pk=None):
        """Check if a crisis report is a duplicate"""
        instance = self.get_object()
        is_dup, matched_id, reason = is_duplicate_report(instance)
        
        response_data = {
            'report_id': str(instance.report_id),
            'is_duplicate': is_dup,
            'reason': reason,
        }
        if matched_id:
            response_data['matched_report_id'] = str(matched_id)
            try:
                matched = FinalCrisisReport.objects.get(report_id=matched_id)
                response_data['matched_report'] = FinalCrisisReportSerializer(matched).data
            except FinalCrisisReport.DoesNotExist:
                pass
        
        return Response(response_data)


# ==================================================
# FINAL CRISIS REPORT API (Dashboard/Verified Reports)
# ==================================================
class FinalCrisisReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Final, verified crisis reports ready for dashboard display.
    Automatically created when CrisisReport is confirmed as non-duplicate.
    """
    queryset = FinalCrisisReport.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ai_disaster_type', 'ai_damage_severity', 'infrastructure_type', 'nature_of_crisis', 'building_footprint_id']
    search_fields = ['building_footprint_id', 'location_description', 'infrastructure_type']
    ordering_fields = ['submitted_at', 'damage_level', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return FinalCrisisReportListSerializer
        return FinalCrisisReportSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistics about final reports"""
        return Response({
            "total": FinalCrisisReport.objects.count(),
            "with_ai_analysis": FinalCrisisReport.objects.exclude(ai_disaster_type__isnull=True).count(),
            "critical_damage": FinalCrisisReport.objects.filter(damage_level="complete").count(),
            "by_disaster_type": dict(
                FinalCrisisReport.objects.values_list('ai_disaster_type').annotate(count=models.Count('report_id'))
            ),
        })

    @action(detail=False, methods=['get'])
    def by_footprint(self, request):
        """Get final reports for a specific building footprint"""
        bf = request.query_params.get('building_footprint_id')
        if not bf:
            return Response(
                {'error': 'building_footprint_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = FinalCrisisReport.objects.filter(building_footprint_id=bf)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def geometry(self, request):
        """Get all final reports with geometry for mapping (GeoJSON-like)"""
        qs = FinalCrisisReport.objects.all()
        serializer = FinalCrisisReportListSerializer(qs, many=True)
        return Response({
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': item['geometry'],
                    'properties': {k: v for k, v in item.items() if k != 'geometry'}
                }
                for item in serializer.data
            ]
        })


# ==================================================
# RESPONDER API
# ==================================================
class ResponderViewSet(viewsets.ModelViewSet):
    queryset = Responder.objects.all()
    serializer_class = ResponderSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'email', 'role']

    @action(detail=False, methods=['get'])
    def nearest(self, request):
        """Find nearest responders to a given location"""
        from .models import get_nearest_responders
        
        # Get coordinates from query params: ?lon=56.78&lat=12.34&max_distance=5000&limit=5
        try:
            lon = float(request.query_params.get('lon'))
            lat = float(request.query_params.get('lat'))
            max_distance = float(request.query_params.get('max_distance', 5000))
            limit = int(request.query_params.get('limit', 5))
        except (TypeError, ValueError):
            return Response(
                {'error': 'Invalid parameters. Required: lon (float), lat (float). Optional: max_distance (meters), limit (int)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate coordinates
        if lat < -90 or lat > 90:
            return Response({'error': 'Invalid latitude. Must be between -90 and 90.'}, status=status.HTTP_400_BAD_REQUEST)
        if lon < -180 or lon > 180:
            return Response({'error': 'Invalid longitude. Must be between -180 and 180.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find nearest responders
        responders_with_distances = get_nearest_responders([lon, lat], max_distance, limit)
        
        response_data = []
        for responder, distance in responders_with_distances:
            serializer = ResponderSerializer(responder)
            data = serializer.data
            data['distance_meters'] = round(distance, 2)
            response_data.append(data)
        
        return Response({
            'query_location': {'longitude': lon, 'latitude': lat},
            'search_radius_meters': max_distance,
            'responders_found': len(response_data),
            'responders': response_data
        })


# ==================================================
# ASSIGNMENT API
# ==================================================
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['assigned_at', 'priority']

    @action(detail=False, methods=['get'])
    def by_responder(self, request):
        responder_id = request.query_params.get("responder_id")
        qs = Assignment.objects.filter(responder__responder_id=responder_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# ==================================================
# LEAFLET MAP VIEW
# ==================================================
class MapView(TemplateView):
    """Crisis reports visualization using Leaflet map"""
    template_name = 'map.html'


# ==================================================
# 404 ERROR HANDLER
# ==================================================
def page_not_found(request, exception=None):
    """Custom 404 error handler"""
    # For API requests, return JSON
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Not Found',
            'detail': 'The requested resource was not found',
            'path': request.path,
            'method': request.method,
            'status': 404
        }, status=404)
    
    # For other requests, try to render 404.html
    from django.shortcuts import render
    return render(request, '404.html', status=404)


def server_error(request):
    """Custom 500 error handler"""
    # For API requests, return JSON
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Internal Server Error',
            'detail': 'An unexpected error occurred on the server',
            'status': 500
        }, status=500)
    
    # For other requests, try to render 500.html
    from django.shortcuts import render
    return render(request, '500.html', status=500)