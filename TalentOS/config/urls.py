"""URL configuration for ATS System."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from apps.shared.health import health_check, readiness_check, HealthCheckView
from apps.shared.hrm_webhook import HRMWebhookView
from apps.shared.hrm_bridge_views import HRMEmployeeTerminatedView, HRMEmployeeCreatedView
from apps.shared.exports import ExportCandidatesView, ExportJobsView, ExportApplicationsView
from apps.shared.imports import ImportCandidatesView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.shared.scorecard_api import (
    scorecard_template_list,
    scorecard_template_detail,
    scorecard_submission_list,
    scorecard_aggregate,
)

urlpatterns = [
    # Prometheus metrics
    path('', include('django_prometheus.urls')),
    # Health checks (no auth)
    path("health/", HealthCheckView.as_view(), name="health"),
    path("ready/", readiness_check, name="readiness"),
    path("admin/", admin.site.urls),
    # API v1
    # ConnectOS unified auth (token, refresh, verify, me, portal-switch)
    path("api/v1/platform-auth/", include("platform_auth.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/tenants/", include("apps.tenants.urls")),
    path("api/v1/jobs/", include("apps.jobs.urls")),
    path("api/v1/candidates/", include("apps.candidates.urls")),
    path("api/v1/applications/", include("apps.applications.urls")),
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/messaging/", include("apps.messaging.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/portal/", include("apps.portal.urls")),
    path("api/v1/scoring/", include("apps.scoring.urls")),
    path("api/v1/blog/", include("apps.blog.urls")),
    path("api/v1/workflows/", include("apps.workflows.urls")),
    # Phase 3 endpoints
    path("api/v1/interviews/", include("apps.applications.api_interviews")),
    path("api/v1/offers/", include("apps.applications.api_offers")),
    path("api/v1/team/", include("apps.applications.api_team")),
    # Gap-fill: debrief, calibration, appeals, HM notes
    path("api/v1/debriefs/", include("apps.applications.api_debriefs")),
    path("api/v1/calibrations/", include("apps.applications.api_calibrations")),
    path("api/v1/appeals/", include("apps.applications.api_appeals")),
    path("api/v1/hm-notes/", include("apps.applications.api_hm_notes")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/admin/", include("apps.notifications.compliance_urls")),
    # GDPR / Consent
    path("api/v1/consent/", include("apps.consent.urls")),
    # Taxonomy (skills, titles, locations)
    path("api/v1/taxonomy/", include("apps.taxonomy.urls")),
    # Bulk actions + advanced APIs
    path("api/v1/", include("apps.shared.urls")),
    # New TalentOS Hiring Cloud apps
    path("api/v1/job-architecture/", include("apps.job_architecture.urls")),
    path("api/v1/compensation/", include("apps.compensation_ops.urls")),
    path("api/v1/crm/", include("apps.talent_crm.urls")),
    path("api/v1/referrals/", include("apps.referrals.urls")),
    path("api/v1/assessments/", include("apps.assessments.urls")),
    path("api/v1/vendors/", include("apps.vendor_management.urls")),
    path("api/v1/marketing/", include("apps.recruitment_marketing.urls")),
    path("api/v1/trust/", include("apps.trust_ops.urls")),
    path("api/v1/compliance-ai/", include("apps.compliance_ai.urls")),
    path("api/v1/internal/", include("apps.internal_recruiting.urls")),
    path("api/v1/forecasting/", include("apps.analytics_forecasting.urls")),
    path("api/v1/accessibility/", include("apps.accessibility_ops.urls")),
    path("api/v1/sourcing/", include("apps.sourcing_crm.urls")),
    path("api/v1/interview-ops/", include("apps.interview_ops.urls")),
    path("api/v1/hm/", include("apps.hm_workspace.urls")),
    path("api/v1/comp-ops/", include("apps.comp_ops.urls")),
    path("api/v1/bridge/", include("apps.internal_bridge.urls")),
    # Inbound HRM webhook receiver (bi-directional sync: terminated employees, employee ID back-write)
    path("api/v1/integrations/hrm/webhook/", HRMWebhookView.as_view(), name="hrm-webhook"),
    path("api/v1/integrations/hrm/employee-terminated", HRMEmployeeTerminatedView.as_view(), name="hrm-employee-terminated"),
    path("api/v1/integrations/hrm/employee-created", HRMEmployeeCreatedView.as_view(), name="hrm-employee-created"),
    # Data exports
    path('api/v1/export/candidates/', ExportCandidatesView.as_view(), name='export-candidates'),
    path('api/v1/export/jobs/', ExportJobsView.as_view(), name='export-jobs'),
    path('api/v1/export/applications/', ExportApplicationsView.as_view(), name='export-applications'),
    path('api/v1/import/candidates/', ImportCandidatesView.as_view(), name='import-candidates'),
    # Subscription & Billing
    path('api/v1/subscription/', include('apps.accounts.subscription_urls')),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Scorecard API
    path("api/v1/scorecards/templates/", scorecard_template_list, name="scorecard-templates"),
    path("api/v1/scorecards/templates/<str:template_id>/", scorecard_template_detail, name="scorecard-template-detail"),
    path("api/v1/scorecards/submissions/", scorecard_submission_list, name="scorecard-submissions"),
    path("api/v1/scorecards/aggregate/<str:candidate_id>/", scorecard_aggregate, name="scorecard-aggregate"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


