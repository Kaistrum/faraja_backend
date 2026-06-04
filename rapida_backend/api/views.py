from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.http import JsonResponse

from .models import CrisisReport, Responder, Assignment
from .serializers import (
    CrisisReportSerializer,
    ResponderSerializer,
    AssignmentSerializer
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
    serializer_class = CrisisReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['event_name', 'damage_level', 'nature_of_crisis']
    ordering_fields = ['created_at', 'damage_level']

    def get_queryset(self):
        return CrisisReport.objects.filter(is_latest=True)

    def create(self, request, *args, **kwargs):
        """Override create to provide better error handling"""
        try:
            return super().create(request, *args, **kwargs)
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
            "pending": CrisisReport.objects.filter(status="pending").count(),
            "resolved": CrisisReport.objects.filter(status="resolved").count(),
            "critical": CrisisReport.objects.filter(damage_level="complete").count(),
        })

    @action(detail=False, methods=['get'])
    def by_event(self, request):
        event_id = request.query_params.get("event_id")
        qs = CrisisReport.objects.filter(event_id=event_id)
        serializer = self.get_serializer(qs, many=True)
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