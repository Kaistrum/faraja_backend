# RAPIDA Django API Setup Guide
**Django + Docker + Swagger on Ubuntu Linux Server**

---

## Project Structure
```
/home/rapida
├── rapida/               ← Django project (auto-generated)
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api/                  ← Django app (auto-generated)
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── nginx.conf
└── .env
```

---

## Step 1 — Create Project Directory

```bash
mkdir -p /home/rapida
cd /home/rapida
```

---

## Step 2 — requirements.txt

```bash
nano requirements.txt
```

Paste:
```txt
Django==4.2
djangorestframework==3.15.1
psycopg2-binary==2.9.9
django-cors-headers==4.3.1
Pillow==10.3.0
python-dotenv==1.0.1
gunicorn==22.0.0
django-environ==0.11.2
drf-yasg==1.21.7
django-filter==23.5
```

Save: `CTRL+X → Y → Enter`

---

## Step 3 — Dockerfile

```bash
nano Dockerfile
```

Paste:
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
```

Save: `CTRL+X → Y → Enter`

---

## Step 4 — .env

```bash
nano .env
```

Paste — replace values with yours:
```env
DEBUG=True
SECRET_KEY=your-very-secret-key-change-this
ALLOWED_HOSTS=5.189.150.44,localhost,127.0.0.1

DB_NAME=rapida_db
DB_USER=rapida_user
DB_PASSWORD=your_strong_password_here
DB_HOST=5.189.150.44
DB_PORT=5432
```

Save: `CTRL+X → Y → Enter`

---

## Step 5 — docker-compose.yml

```bash
nano docker-compose.yml
```

Paste:
```yaml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn rapida.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - ./media:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./media:/app/media
    depends_on:
      - web
    restart: always
```

Save: `CTRL+X → Y → Enter`

---

## Step 6 — nginx.conf

```bash
nano nginx.conf
```

Paste:
```nginx
server {
    listen 80;
    server_name 5.189.150.44;

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

Save: `CTRL+X → Y → Enter`

---

## Step 7 — Generate Django Project

```bash
docker-compose run web django-admin startproject rapida .
```

This auto-generates the `rapida/` settings package and `manage.py`.

---

## Step 8 — Update settings.py

```bash
nano rapida/settings.py
```

Replace entire file with:
```python
import environ
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    'drf_yasg',
    'django_filters',
    # Local
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rapida.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rapida.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    }
}
```

Save: `CTRL+X → Y → Enter`

---

## Step 9 — Update rapida/urls.py

```bash
nano rapida/urls.py
```

Paste:
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="RAPIDA API",
        default_version='v1',
        description="UNDP RAPIDA Crisis Damage Assessment API",
        contact=openapi.Contact(email="admin@rapida.org"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # Swagger UI
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # ReDoc UI
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

Save: `CTRL+X → Y → Enter`

---

## Step 10 — Create the API App

```bash
docker-compose run web python manage.py startapp api
```

---

## Step 11 — api/models.py

> ⚠️ **Important:** `managed = False` tells Django NOT to create or modify
> the tables since they already exist in your database. Your existing
> schema and data will be completely safe.

```bash
nano api/models.py
```

Paste:
```python
import uuid
from django.db import models


class CrisisReport(models.Model):
    INFRASTRUCTURE_TYPES = [
        ('residential', 'Residential Infrastructure'),
        ('commercial', 'Commercial Infrastructure'),
        ('government', 'Government Building'),
        ('utility', 'Utility Infrastructure'),
        ('transport_communication', 'Transport and Communication Infrastructure'),
        ('community', 'Community Infrastructure'),
        ('public_recreation', 'Public spaces/Recreation Infrastructure'),
        ('other', 'Other'),
    ]

    NATURE_OF_CRISIS = [
        ('earthquake', 'Earthquake'),
        ('flood', 'Flood'),
        ('tsunami', 'Tsunami'),
        ('hurricane_cyclone', 'Hurricane/Cyclone'),
        ('wildfire', 'Wildfire'),
        ('explosion', 'Explosion'),
        ('chemical_incident', 'Chemical Incident'),
        ('conflict', 'Conflict'),
        ('civil_unrest', 'Civil Unrest'),
    ]

    DAMAGE_LEVELS = [
        ('minimal', 'Minimal/No Damage'),
        ('partial', 'Partially Damaged'),
        ('complete', 'Completely Damaged'),
    ]

    RESPONDENCE_STATUS = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    SUBMISSION_CHANNELS = [
        ('web', 'Web'),
        ('mobile', 'Mobile'),
        ('whatsapp', 'WhatsApp'),
        ('offline_sync', 'Offline Sync'),
    ]

    LANGUAGES = [
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('fr', 'French'),
        ('zh', 'Chinese'),
        ('ru', 'Russian'),
        ('es', 'Spanish'),
    ]

    # Identity
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_name = models.CharField(max_length=200)
    event_id = models.CharField(max_length=100)

    # Versioning
    version_number = models.IntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    previous_report = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='next_versions'
    )

    # Location
    lat = models.FloatField(null=True, blank=True)
    long = models.FloatField(null=True, blank=True)
    location_text = models.TextField(null=True, blank=True)
    fishnet_id = models.CharField(max_length=50, null=True, blank=True)

    # Infrastructure
    infrastructure_type = models.CharField(max_length=100, choices=INFRASTRUCTURE_TYPES)
    infrastructure_type_other = models.TextField(null=True, blank=True)
    infrastructure_name = models.CharField(max_length=200, null=True, blank=True)
    no_of_damaged_infrastructures = models.IntegerField(default=1)

    # Crisis Classification
    nature_of_crisis = models.CharField(max_length=50, choices=NATURE_OF_CRISIS)

    # Damage
    damage_level = models.CharField(max_length=20, choices=DAMAGE_LEVELS)
    debris_needs_clearing = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    # Media
    photos = models.JSONField(default=list)

    # AI Analysis
    ai_damage_level = models.CharField(max_length=20, null=True, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    ai_description = models.TextField(null=True, blank=True)

    # Submitter
    submitter_token = models.CharField(max_length=255, null=True, blank=True)
    submission_channel = models.CharField(max_length=50, choices=SUBMISSION_CHANNELS, null=True, blank=True)
    language = models.CharField(max_length=10, choices=LANGUAGES, null=True, blank=True)

    # Duplicate Detection
    is_duplicate = models.BooleanField(default=False)
    duplicate_of_report = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicates'
    )

    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Modular Questions
    custom_responses = models.JSONField(default=dict)

    # Response Status
    respondence_status = models.CharField(
        max_length=50, choices=RESPONDENCE_STATUS, default='pending'
    )
    respondence_time = models.DateTimeField(null=True, blank=True)

    # Timestamps
    submission_timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crisis_report'
        managed = False
        ordering = ['-submission_timestamp']

    def __str__(self):
        return f"{self.event_name} - {self.damage_level} - {self.report_id}"


class Responder(models.Model):
    ROLES = [
        ('admin', 'Admin'),
        ('field_enumerator', 'Field Enumerator'),
        ('analyst', 'Analyst'),
        ('supervisor', 'Supervisor'),
    ]

    responder_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    responder_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=50, choices=ROLES)
    organization = models.CharField(max_length=150, null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'responders'
        managed = False

    def __str__(self):
        return f"{self.responder_name} ({self.role})"


class Assignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(CrisisReport, on_delete=models.CASCADE, related_name='assignments')
    responder = models.ForeignKey(Responder, on_delete=models.CASCADE, related_name='assignments')
    assigned_by = models.ForeignKey(
        Responder, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    notes = models.TextField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'assignment'
        managed = False

    def __str__(self):
        return f"Assignment {self.assignment_id} - {self.status}"
```

Save: `CTRL+X → Y → Enter`

---

## Step 12 — api/serializers.py

```bash
nano api/serializers.py
```

Paste:
```python
from rest_framework import serializers
from .models import CrisisReport, Responder, Assignment


class CrisisReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrisisReport
        fields = '__all__'
        read_only_fields = ['report_id', 'submission_timestamp', 'last_updated']


class ResponderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responder
        fields = '__all__'
        extra_kwargs = {
            'password_hash': {'write_only': True}
        }


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ['assignment_id', 'assigned_at']
```

Save: `CTRL+X → Y → Enter`

---

## Step 13 — api/views.py

```bash
nano api/views.py
```

Paste:
```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import CrisisReport, Responder, Assignment
from .serializers import CrisisReportSerializer, ResponderSerializer, AssignmentSerializer


class CrisisReportViewSet(viewsets.ModelViewSet):
    queryset = CrisisReport.objects.filter(is_latest=True, is_duplicate=False)
    serializer_class = CrisisReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['event_name', 'infrastructure_type', 'damage_level', 'nature_of_crisis']
    ordering_fields = ['submission_timestamp', 'damage_level']

    @swagger_auto_schema(
        operation_summary="List all latest crisis reports",
        operation_description="Returns all latest, non-duplicate crisis reports."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Submit a new crisis report",
        operation_description="Submit a new damage report from the community."
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='by-event/(?P<event_id>[^/.]+)')
    def by_event(self, request, event_id=None):
        """Get all reports for a specific crisis event"""
        reports = CrisisReport.objects.filter(event_id=event_id, is_latest=True)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Get dashboard statistics"""
        total = CrisisReport.objects.filter(is_latest=True, is_duplicate=False).count()
        minimal = CrisisReport.objects.filter(damage_level='minimal', is_latest=True).count()
        partial = CrisisReport.objects.filter(damage_level='partial', is_latest=True).count()
        complete = CrisisReport.objects.filter(damage_level='complete', is_latest=True).count()
        return Response({
            'total_reports': total,
            'minimal_damage': minimal,
            'partial_damage': partial,
            'complete_damage': complete,
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """Export all latest reports for UNDP"""
        reports = CrisisReport.objects.filter(is_latest=True, is_duplicate=False).values(
            'report_id', 'event_id', 'event_name', 'nature_of_crisis',
            'infrastructure_type', 'infrastructure_name', 'damage_level',
            'debris_needs_clearing', 'description', 'lat', 'long',
            'location_text', 'submission_channel', 'language',
            'respondence_status', 'submission_timestamp',
            'version_number', 'is_verified', 'custom_responses'
        )
        return Response(list(reports))


class ResponderViewSet(viewsets.ModelViewSet):
    queryset = Responder.objects.filter(active=True)
    serializer_class = ResponderSerializer

    @swagger_auto_schema(operation_summary="List all active responders")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['assigned_at', 'due_date', 'priority']

    @swagger_auto_schema(operation_summary="List all assignments")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='by-responder/(?P<responder_id>[^/.]+)')
    def by_responder(self, request, responder_id=None):
        """Get all assignments for a specific responder"""
        assignments = Assignment.objects.filter(responder__responder_id=responder_id)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
```

Save: `CTRL+X → Y → Enter`

---

## Step 14 — api/urls.py

```bash
nano api/urls.py
```

Paste:
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrisisReportViewSet, ResponderViewSet, AssignmentViewSet

router = DefaultRouter()
router.register(r'reports', CrisisReportViewSet, basename='reports')
router.register(r'responders', ResponderViewSet, basename='responders')
router.register(r'assignments', AssignmentViewSet, basename='assignments')

urlpatterns = [
    path('', include(router.urls)),
]
```

Save: `CTRL+X → Y → Enter`

---

## Step 15 — Build & Run

```bash
# Build Docker image
docker-compose build

# Run migrations (only Django internal tables, NOT your existing tables)
docker-compose run web python manage.py migrate

# Create superuser for Django Admin
docker-compose run web python manage.py createsuperuser

# Start everything
docker-compose up -d
```

---

## Step 16 — Verify Running

```bash
# Check containers are running
docker-compose ps

# Check logs
docker-compose logs web
```

---

## Step 17 — Access Your API

| URL | Description |
|---|---|
| `http://5.189.150.44/api/` | API root |
| `http://5.189.150.44/api/reports/` | Crisis reports |
| `http://5.189.150.44/api/reports/stats/` | Dashboard statistics |
| `http://5.189.150.44/api/reports/export/` | Export for UNDP |
| `http://5.189.150.44/api/responders/` | Responders |
| `http://5.189.150.44/api/assignments/` | Assignments |
| `http://5.189.150.44/swagger/` | Swagger UI |
| `http://5.189.150.44/redoc/` | ReDoc UI |
| `http://5.189.150.44/admin/` | Django Admin |

---

## Important Notes

### managed = False
All 3 models have `managed = False` in their Meta class. This means:
- Django will **NOT** create or modify your existing tables
- Your existing schema, indexes, views and triggers are completely safe
- Django can still read and write data normally

### Photos
Photos are stored as a JSONB array of local file paths:
```json
[
  {
    "url": "/media/reports/photo1.jpg",
    "thumbnail_url": "/media/reports/photo1_thumb.jpg",
    "is_primary": true,
    "uploaded_at": "2026-06-04T10:00:00Z"
  }
]
```

### Versioning
When a new report is submitted for the same location:
1. New report is inserted with `previous_report_id` pointing to old report
2. Database trigger automatically sets old report's `is_latest = FALSE`
3. API always queries `is_latest = TRUE` for dashboard and exports
