from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from api.views import LandingPageView, MapView, page_not_found, server_error
from api.admin import rapida_admin

urlpatterns = [
    # Landing page
    path('', LandingPageView.as_view(), name='home'),
    
    # Map visualization
    path('map/', MapView.as_view(), name='map'),
    
    path('admin/', rapida_admin.urls),
    path('api/', include('api.urls')),
    
    # Swagger/OpenAPI documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Custom error handlers
handler404 = page_not_found
handler500 = server_error