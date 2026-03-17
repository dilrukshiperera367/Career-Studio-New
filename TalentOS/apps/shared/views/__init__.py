"""
apps/shared/views
=================
Split view package.  All public names are re-exported so that
``apps/shared/api.py`` (and anything else) can still do::

    from apps.shared.views import SomeView
    # or
    from apps.shared.api import analytics_urlpatterns  # still works via api.py

Sub-modules
-----------
messaging      — MessageViewSet, EmailTemplateViewSet, messaging_urlpatterns
analytics      — KPI, funnel, ROI, data-quality views, analytics_urlpatterns
portal         — public candidate-facing views, portal_urlpatterns
notifications  — in-app + unified ATS/HRM feed, notification_urlpatterns
audits         — login audit, GDPR/compliance helpers, compliance_urlpatterns
offers         — PortalOfferReviewView
referrals      — PortalReferralView
onboarding     — EarlyAttritionView, BuddySuggestionView
misc           — InterviewConflictView
"""

# --- messaging ---------------------------------------------------------------
from apps.shared.views.messaging import (  # noqa: F401
    MessageSerializer,
    EmailTemplateSerializer,
    MessageViewSet,
    EmailTemplateViewSet,
    messaging_router,
    messaging_urlpatterns,
)

# --- analytics ---------------------------------------------------------------
from apps.shared.views.analytics import (  # noqa: F401
    AnalyticsDailySerializer,
    SavedReportSerializer,
    AnalyticsView,
    FunnelView,
    KPIDashboardView,
    RecruiterPerformanceView,
    PipelineVelocityView,
    DiversityMetricsView,
    SourceROIView,
    SLAComplianceView,
    HiringForecastView,
    AnalyticsExportView,
    SavedReportListView,
    SavedReportDetailView,
    TrendReportView,
    RejectionAnalyticsView,
    InterviewToHireRatioView,
    OfferComparisonView,
    VotingTallyView,
    ScoreComparisonView,
    BatchRescoreView,
    CostPerHireView,
    DataCleanupView,
    ContactValidationView,
    StaleDataFlaggingView,
    GDPRPurgeView,
    analytics_urlpatterns,
)

# --- portal ------------------------------------------------------------------
from apps.shared.views.portal import (  # noqa: F401
    PortalApplySerializer,
    PortalApplyView,
    PortalStatusView,
    PortalJobAlertView,
    PortalFeedbackView,
    PortalCareerPageView,
    PortalDocumentUploadView,
    PortalProfileUpdateView,
    PortalSelfScheduleView,
    portal_urlpatterns,
)

# --- notifications -----------------------------------------------------------
from apps.shared.views.notifications import (  # noqa: F401
    NotificationSerializer,
    NotificationPreferenceSerializer,
    NotificationListView,
    NotificationPreferencesView,
    UnifiedNotificationView,
    notification_urlpatterns,
)

# --- audits / compliance -----------------------------------------------------
from apps.shared.views.audits import (  # noqa: F401
    LoginAuditView,
    RateLimitConfigView,
    JobShareLinkView,
    compliance_urlpatterns,
)

# --- offers ------------------------------------------------------------------
from apps.shared.views.offers import (  # noqa: F401
    PortalOfferReviewView,
)

# --- referrals ---------------------------------------------------------------
from apps.shared.views.referrals import (  # noqa: F401
    PortalReferralView,
)

# --- onboarding --------------------------------------------------------------
from apps.shared.views.onboarding import (  # noqa: F401
    EarlyAttritionView,
    BuddySuggestionView,
)

# --- misc --------------------------------------------------------------------
from apps.shared.views.misc import (  # noqa: F401
    InterviewConflictView,
)
