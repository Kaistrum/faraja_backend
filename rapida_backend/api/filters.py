import django_filters
from .models import CrisisReport


class CrisisReportFilter(django_filters.FilterSet):
    class Meta:
        model = CrisisReport
        fields = {
            'ai_disaster_type': ['exact', 'in'],
            'ai_damage_severity': ['exact', 'in'],
            'ai_informativeness': ['exact', 'in'],
            'building_footprint_id': ['exact', 'icontains'],
            'nature_of_crisis': ['exact', 'in'],
            'submitted_at': ['gte', 'lte'],
        }
