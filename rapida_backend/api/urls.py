from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CrisisReportViewSet, ResponderViewSet, AssignmentViewSet

router = DefaultRouter()
router.register(r'reports', CrisisReportViewSet)
router.register(r'responders', ResponderViewSet)
router.register(r'assignments', AssignmentViewSet)

urlpatterns = router.urls