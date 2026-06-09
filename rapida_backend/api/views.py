from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from django_filters.rest_framework import DjangoFilterBackend

from .models import CrisisReport, Responder, Assignment
from .serializers import (
    SubmitSerializer,
    FullSerializer,
    CrisisReportGeoSerializer,
    CrisisReportListSerializer,
    ResponderSerializer,
    AssignmentSerializer,
)


# ==================================================
# LANDING PAGE
# ==================================================
class LandingPageView(APIView):
    """Landing page showing all available endpoints"""
    
    def get(self, request):
        return Response({
            "title": "RAPIDA API",
            "description": "UNDP Crisis Damage Assessment API",
            "version": "1.0.0",
            "endpoints": {
                "documentation": {
                    "Swagger UI": "http://" + request.get_host() + "/api/schema/swagger-ui/",
                    "ReDoc": "http://" + request.get_host() + "/api/schema/redoc/",
                },
                "visualization": {
                    "Crisis Map": "http://" + request.get_host() + "/map/",
                },
                "api": {
                    "Crisis Reports": "http://" + request.get_host() + "/api/reports/",
                    "Responders": "http://" + request.get_host() + "/api/responders/",
                    "Assignments": "http://" + request.get_host() + "/api/assignments/",
                },
                "admin": {
                    "Admin Panel": "http://" + request.get_host() + "/admin/",
                }
            },
            "message": "Visit the Swagger UI or Admin Panel above"
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


# ==================================================
# RESPONDER API
# ==================================================
class ResponderViewSet(viewsets.ModelViewSet):
    queryset = Responder.objects.all()
    serializer_class = ResponderSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'email', 'role']


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