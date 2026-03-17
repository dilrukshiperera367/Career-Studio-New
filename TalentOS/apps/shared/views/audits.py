"""Audit, compliance, and miscellaneous admin views."""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path

from apps.accounts.permissions import HasTenantAccess


# ---------------------------------------------------------------------------
# Login audit trail (Feature 136)
# ---------------------------------------------------------------------------

class LoginAuditView(APIView):
    """View login audit trail for the tenant."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.shared.models import AuditLog

        logs = AuditLog.objects.filter(
            tenant_id=request.tenant_id,
            action__in=["login", "logout"],
        ).order_by("-timestamp")[:100]

        return Response([
            {
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "ip_address": log.ip_address or "",
                "user_agent": log.user_agent or "",
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ])


# ---------------------------------------------------------------------------
# API rate-limiting config (Feature 138)
# ---------------------------------------------------------------------------

class RateLimitConfigView(APIView):
    """View and configure API rate limits."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from django.conf import settings
        throttle_config = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
        return Response({
            "throttle_rates": throttle_config,
            "rate_limit_enabled": bool(throttle_config),
        })


# ---------------------------------------------------------------------------
# Job sharing link (Feature 37)
# ---------------------------------------------------------------------------

class JobShareLinkView(APIView):
    """Generate shareable public link for a job."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request, pk):
        from apps.jobs.models import Job

        try:
            job = Job.objects.get(id=pk, tenant_id=request.tenant_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)

        # Increment view counter
        job.view_count = (job.view_count or 0) + 1
        job.save(update_fields=["view_count"])

        share_url = f"/portal/career-page/?tenant={job.tenant.slug}#job-{job.id}"
        return Response({
            "job_id": str(job.id),
            "title": job.title,
            "share_url": share_url,
            "view_count": job.view_count,
        })


# ---------------------------------------------------------------------------
# Compliance URL patterns (used by apps/notifications/compliance_urls.py)
# ---------------------------------------------------------------------------

# Imported here to avoid circular issues; analytics.py is a sibling module
from apps.shared.views.analytics import (  # noqa: E402
    ContactValidationView,
    GDPRPurgeView,
)
from apps.shared.views.gdpr import (  # noqa: E402
    GDPRDataExportView,
    GDPRDataEraseView,
    DataSubjectRequestListView,
    DataSubjectRequestProcessView,
)
from apps.shared.views.onboarding import BuddySuggestionView  # noqa: E402

compliance_urlpatterns = [
    path("validate-contact/<uuid:pk>/", ContactValidationView.as_view(), name="validate-contact"),
    path("gdpr-purge/<uuid:pk>/", GDPRPurgeView.as_view(), name="gdpr-purge"),
    # GDPR right of access / right to erasure / data subject requests (#49, #50)
    path("gdpr/export/<uuid:pk>/", GDPRDataExportView.as_view(), name="gdpr-export"),
    path("gdpr/erase/<uuid:pk>/", GDPRDataEraseView.as_view(), name="gdpr-erase"),
    path("gdpr/requests/", DataSubjectRequestListView.as_view(), name="gdpr-requests"),
    path("gdpr/requests/<uuid:pk>/process/", DataSubjectRequestProcessView.as_view(), name="gdpr-request-process"),
    path("login-audit/", LoginAuditView.as_view(), name="login-audit"),
    path("rate-limits/", RateLimitConfigView.as_view(), name="rate-limits"),
    path("buddy-suggestion/<uuid:pk>/", BuddySuggestionView.as_view(), name="buddy-suggestion"),
    path("job-share/<uuid:pk>/", JobShareLinkView.as_view(), name="job-share"),
]
