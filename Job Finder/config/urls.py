"""URL Configuration for Job Finder."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.shared.views import health_check, api_root

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    # ── ConnectOS unified auth ─────────────────────────────────────────────────
    path("api/v1/platform-auth/", include("platform_auth.urls")),
    # ── API v1 ─────────────────────────────────────────────────────────────
    path("api/v1/", api_root, name="api-root"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/taxonomy/", include("apps.taxonomy.urls")),
    path("api/v1/candidates/", include("apps.candidates.urls")),
    path("api/v1/employers/", include("apps.employers.urls")),
    path("api/v1/jobs/", include("apps.jobs.urls")),
    path("api/v1/applications/", include("apps.applications.urls")),
    path("api/v1/ats-connector/", include("apps.ats_connector.urls")),
    path("api/v1/reviews/", include("apps.reviews.urls")),
    path("api/v1/content/", include("apps.content.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/messaging/", include("apps.messaging.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/moderation/", include("apps.moderation.urls")),
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/assessments/", include("apps.assessments.urls")),
    path("api/v1/ai-tools/", include("apps.ai_tools.urls")),
    path("api/v1/governance/", include("apps.governance.urls")),

    # ── Shared Foundation APIs ──
    path("api/v1/workflows/", include("apps.engine.workflows.urls")),
    path("api/v1/communications/", include("apps.engine.communications.urls")),
    path("api/v1/trust/", include("apps.trust.verification.urls")),
    # ── Core APIs ──
    path("api/v1/credentials/", include("apps.core.credentials.urls")),
    path("api/v1/consent/", include("apps.consent.urls")),

    # ── New Marketplace APIs ──
    path("api/v1/marketplace-search/", include("apps.marketplace_search.urls")),
    path("api/v1/seo/", include("apps.seo_indexing.urls")),
    path("api/v1/job-quality/", include("apps.job_quality.urls")),
    path("api/v1/billing/", include("apps.marketplace_billing.urls")),
    path("api/v1/company-intel/", include("apps.company_intelligence.urls")),
    path("api/v1/salary/", include("apps.salary_intelligence.urls")),
    path("api/v1/promotions/", include("apps.promotions_ads.urls")),
    path("api/v1/trust-ops/", include("apps.trust_ops.urls")),
    path("api/v1/retention/", include("apps.retention_growth.urls")),
    path("api/v1/mobile/", include("apps.mobile_api.urls")),
    path("api/v1/marketplace-analytics/", include("apps.marketplace_analytics.urls")),
    path("api/v1/feed-norm/", include("apps.feed_normalization.urls")),
    path("api/v1/ops/", include("apps.admin_panel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
