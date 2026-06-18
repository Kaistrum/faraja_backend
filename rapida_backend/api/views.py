from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from django.contrib.auth.hashers import check_password
from datetime import timedelta

from django_filters.rest_framework import DjangoFilterBackend

from .models import CrisisReport, Responder, Assignment, FinalCrisisReport, is_duplicate_report
from .serializers import (
    SubmitSerializer,
    FullSerializer,
    CrisisReportListSerializer,
    ResponderSerializer,
    AssignmentSerializer,
    FinalCrisisReportSerializer,
    FinalCrisisReportListSerializer,
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
            "docs": f"{base}/api/schema/swagger-ui/",
            "endpoints": {
                "Crisis Reports": f"{base}/api/reports/",
                "Final Reports": f"{base}/api/final-reports/",
                "Responders": f"{base}/api/responders/",
                "Assignments": f"{base}/api/assignments/",
            },
            "schemas": {
                "CrisisReport": {
                    "report_id": "UUID (primary key, auto)",
                    "client_id": "UUID (optional, unique)",
                    "lat": "Float - latitude (write: used to set location)",
                    "lon": "Float - longitude (write: used to set location)",
                    "location": "GeoJSON Point - {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "String",
                    "building_footprint_id": "String",
                    "infrastructure_type": "Enum: residential | commercial | government | utility | transport | community | recreation | other",
                    "nature_of_crisis": "Enum: earthquake | flood | tsunami | cyclone | wildfire | explosion | conflict | civil_unrest | chemical | other",
                    "debris": "Boolean",
                    "affected_units": "Integer",
                    "damage_level": "Enum: minimal | partial | complete",
                    "photo_url": "String (URL)",
                    "submitted_at": "DateTime",
                },
                "FinalCrisisReport": {
                    "report_id": "UUID (primary key, auto)",
                    "original_report_id": "UUID - source CrisisReport",
                    "client_id": "UUID (optional)",
                    "lat": "Float - latitude (read)",
                    "lon": "Float - longitude (read)",
                    "location": "GeoJSON Point - {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "String",
                    "building_footprint_id": "String",
                    "infrastructure_type": "Enum: residential | commercial | government | utility | transport | community | recreation | other",
                    "nature_of_crisis": "Enum: earthquake | flood | tsunami | cyclone | wildfire | explosion | conflict | civil_unrest | chemical | other",
                    "debris": "Boolean",
                    "affected_units": "Integer",
                    "damage_level": "Enum: minimal | partial | complete",
                    "photo_url": "String (URL)",
                    "submitted_at": "DateTime",
                },
                "Responder": {
                    "responder_id": "UUID (primary key, auto)",
                    "name": "String",
                    "email": "Email (unique)",
                    "password_hash": "String (write-only)",
                    "role": "Enum: admin | field | analyst | supervisor",
                    "organization": "String (optional)",
                    "is_active": "Boolean",
                    "lat": "Float - latitude (write: used to set location)",
                    "lon": "Float - longitude (write: used to set location)",
                    "location": "GeoJSON Point - {'type':'Point','coordinates':[lon,lat]}",
                    "location_description": "String",
                }
            }
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
        if self.action == 'list':
            return CrisisReportListSerializer
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
        """Patch AI-populated fields and sync to FinalCrisisReport"""
        instance = self.get_object()
        allowed = ['ai_damage_level', 'ai_disaster_type', 'ai_informativeness', 'ai_humanitarian_category', 'ai_damage_severity']
        for k in allowed:
            if k in request.data:
                setattr(instance, k, request.data.get(k))

        instance.processed_at = timezone.now()
        instance.save()

        # Sync AI fields to the linked FinalCrisisReport
        FinalCrisisReport.objects.filter(original_report_id=instance.report_id).update(
            ai_damage_level=instance.ai_damage_level,
            ai_disaster_type=instance.ai_disaster_type,
            ai_informativeness=instance.ai_informativeness,
            ai_humanitarian_category=instance.ai_humanitarian_category,
            ai_damage_severity=instance.ai_damage_severity,
            processed_at=instance.processed_at,
        )

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
# RESPONDER LOGIN
# ==================================================
class ResponderLoginView(APIView):
    """Authenticate a responder with email and password."""

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'error': 'email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            responder = Responder.objects.get(email__iexact=email)
        except Responder.DoesNotExist:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not responder.is_active:
            return Response(
                {'error': 'Account is inactive.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not check_password(password, responder.password_hash):
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        responder.last_login = timezone.now()
        responder.save(update_fields=['last_login'])

        serializer = ResponderSerializer(responder)
        return Response({
            'message': 'Login successful.',
            'responder': serializer.data,
        }, status=status.HTTP_200_OK)


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