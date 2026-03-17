"""ConnectHR URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from platform_core.health import HealthCheckView
from platform_core.approval_views import ApprovalRequestListView, ApprovalActionView
from core_hr.exports import ExportEmployeesView, ExportLeaveRequestsView, ExportPayrollView
from core_hr.imports import ImportEmployeesView
import time




def readiness_check(request):
    """Readiness probe — returns 200 only when DB is reachable."""
    try:
        start = time.monotonic()
        connection.ensure_connection()
        db_latency = round((time.monotonic() - start) * 1000, 1)
        return JsonResponse({
            "status": "ready",
            "service": "hrm",
            "checks": {"database": {"status": "ok", "latency_ms": db_latency}},
        })
    except Exception as exc:
        return JsonResponse({
            "status": "not_ready",
            "service": "hrm",
            "checks": {"database": {"status": "error", "detail": str(exc)}},
        }, status=503)


urlpatterns = [
    # Prometheus metrics
    path('', include('django_prometheus.urls')),
    # Health & readiness probes
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('ready/', readiness_check, name='readiness'),

    path('admin/', admin.site.urls),

    # API v1
    # ConnectOS unified auth (token, refresh, verify, me, portal-switch)
    path('api/v1/platform-auth/', include('platform_auth.urls')),
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/tenants/', include('tenants.urls')),
    path('api/v1/', include('core_hr.urls')),
    path('api/v1/', include('leave_attendance.urls')),
    path('api/v1/', include('payroll.urls')),
    path('api/v1/', include('onboarding.urls')),
    path('api/v1/', include('performance.urls')),
    path('api/v1/', include('analytics.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    path('api/v1/platform/', include('platform_core.urls')),
    path('api/v1/engagement/', include('engagement.urls')),
    path('api/v1/learning/', include('learning.urls')),
    path('api/v1/helpdesk/', include('helpdesk.urls')),
    path('api/v1/workflows/', include('workflows.urls')),
    path('api/v1/custom-objects/', include('custom_objects.urls')),

    # WorkforceOS expansion apps
    path('api/v1/', include('manager_hub.urls')),
    path('api/v1/', include('employee_hub.urls')),
    path('api/v1/', include('internal_marketplace.urls')),
    path('api/v1/', include('total_rewards.urls')),
    path('api/v1/', include('employee_relations.urls')),
    path('api/v1/', include('people_analytics.urls')),
    path('api/v1/', include('compliance_ai.urls')),
    path('api/v1/', include('workforce_planning.urls')),
    path('api/v1/', include('documents_policies.urls')),
    path('api/v1/', include('experience_hub.urls')),
    path('api/v1/', include('global_workforce.urls')),
    path('api/v1/', include('contingent_ops.urls')),

    # Data exports
    path('api/v1/export/employees/', ExportEmployeesView.as_view(), name='export-employees'),
    path('api/v1/import/employees/', ImportEmployeesView.as_view(), name='import-employees'),
    path('api/v1/export/leave-requests/', ExportLeaveRequestsView.as_view(), name='export-leave'),
    path('api/v1/export/payroll/', ExportPayrollView.as_view(), name='export-payroll'),

    # Standalone approval endpoints (short path, no /platform/ prefix)
    path('api/v1/approvals/', ApprovalRequestListView.as_view(), name='approval-list'),
    path('api/v1/approvals/<uuid:pk>/<str:action>/', ApprovalActionView.as_view(), name='approval-action'),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
