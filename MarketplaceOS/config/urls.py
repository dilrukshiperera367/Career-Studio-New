from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView

urlpatterns = [
    path("admin/", admin.site.urls),

    # ConnectOS unified auth
    path("api/v1/auth/", include("platform_auth.urls")),

    # Auth (legacy)
    path("api/auth/", include("apps.accounts.urls")),

    # Core marketplace
    path("api/", include("apps.providers.urls")),
    path("api/", include("apps.services_catalog.urls")),
    path("api/", include("apps.bookings.urls")),
    path("api/", include("apps.delivery.urls")),

    # Commerce
    path("api/", include("apps.payments.urls")),
    path("api/", include("apps.billing.urls")),

    # Trust & quality
    path("api/", include("apps.reviews.urls")),
    path("api/", include("apps.trust_marketplace.urls")),

    # Specialized marketplaces
    path("api/", include("apps.enterprise_marketplace.urls")),
    path("api/", include("apps.learning_marketplace.urls")),
    path("api/", include("apps.assessment_marketplace.urls")),

    # Communications
    path("api/", include("apps.marketplace_messaging.urls")),

    # Matching + discovery
    path("api/", include("apps.marketplace.urls")),

    # Analytics
    path("api/analytics/", include("apps.marketplace_analytics.urls")),

    # Admin tooling
    path("api/", include("apps.marketplace_admin.urls")),

    # Shared / health
    path("api/", include("apps.shared.urls")),

    # API schema / docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
]
