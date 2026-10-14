from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from accounts.views.auth import CustomTokenObtainPairView


class ProtectedSchemaView(SpectacularAPIView):
    """Keep the API schema private; it exposes the whole data model."""

    permission_classes = [IsAuthenticated, IsAdmin]


class ProtectedSwaggerView(SpectacularSwaggerView):
    permission_classes = [IsAuthenticated, IsAdmin]


class ProtectedRedocView(SpectacularRedocView):
    permission_classes = [IsAuthenticated, IsAdmin]


urlpatterns = [
    path('admin/', admin.site.urls),

    # API Docs (admin-only; the schema leaks endpoints and business rules)
    path('api/schema/', ProtectedSchemaView.as_view(), name='schema'),
    path('api/docs/', ProtectedSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', ProtectedRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth Endpoints (JWT)
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App Endpoints
    path('api/', include('accounts.urls')),
    path('api/', include('bookings.urls')),
    path('api/', include('courts.urls')),
    path('api/', include('vendors.urls')),
    path('api/', include('realtime.urls')),

    # SEO static pages
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('sitemap.xml', TemplateView.as_view(template_name='sitemap.xml', content_type='application/xml')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
