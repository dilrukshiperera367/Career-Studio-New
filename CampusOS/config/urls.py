"""CampusOS — Root URL Configuration."""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

api_v1_patterns = [
    # ConnectOS unified auth
    path("auth/platform/", include("platform_auth.urls")),
    # Auth
    path("auth/", include("apps.accounts.urls")),
    # Core
    path("campus/", include("apps.campus.urls")),
    # P0 modules
    path("students/", include("apps.students.urls")),
    path("readiness/", include("apps.readiness.urls")),
    path("internships/", include("apps.internships.urls")),
    path("placements/", include("apps.placements.urls")),
    path("employers/", include("apps.campus_employers.urls")),
    path("mentors/", include("apps.alumni_mentors.urls")),
    path("outcomes/", include("apps.outcomes_analytics.urls")),
    path("trust/", include("apps.campus_trust.urls")),
    # P1 modules
    path("events/", include("apps.campus_events.urls")),
    path("credentials/", include("apps.credentials_wallet.urls")),
    path("advisors/", include("apps.advisors.urls")),
    path("assessments/", include("apps.assessments.urls")),
    # Integrations
    path("integrations/", include("apps.campus_integrations.urls")),
    # Billing
    path("billing/", include("apps.billing.urls")),
    # Analytics
    path("analytics/", include("apps.analytics.urls")),
    # OpenAPI schema
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
