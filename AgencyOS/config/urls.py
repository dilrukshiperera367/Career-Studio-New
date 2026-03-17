from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    # ConnectOS unified auth (token, refresh, verify, me, portal-switch)
    path("api/v1/auth/", include("platform_auth.urls")),

    # Auth (legacy endpoint — kept for backward compat)
    path("api/auth/", include("apps.accounts.urls")),

    # Core agency operations
    path("api/", include("apps.agencies.urls")),
    path("api/analytics/", include("apps.analytics.urls")),

    # Feature apps
    path("api/crm/", include("apps.agency_crm.urls")),
    path("api/job-orders/", include("apps.job_orders.urls")),
    path("api/submissions/", include("apps.submissions.urls")),
    path("api/client-portal/", include("apps.client_portal.urls")),
    path("api/contractor-ops/", include("apps.contractor_ops.urls")),
    path("api/timesheets/", include("apps.timesheets.urls")),
    path("api/finance/", include("apps.finance_ops.urls")),
    path("api/commissions/", include("apps.commissions.urls")),
    path("api/redeployment/", include("apps.redeployment.urls")),
    path("api/vendor-vms/", include("apps.vendor_vms.urls")),
    path("api/compliance/", include("apps.agency_compliance.urls")),
    path("api/trust/", include("apps.agency_trust.urls")),
    path("api/agency-analytics/", include("apps.agency_analytics.urls")),

    # Shared utilities
    path("api/", include("apps.shared.urls")),

    # API schema / docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
