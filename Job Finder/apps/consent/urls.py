"""Consent & Privacy URL routing — Features 19 (Accessibility, Privacy & Account Safety)."""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from . import views_extra

router = DefaultRouter()
router.register("records", views.ConsentRecordViewSet, basename="consent-record")
router.register("export-requests", views.DataExportRequestViewSet, basename="data-export")
router.register("deletion-requests", views.DataDeletionRequestViewSet, basename="data-deletion")
router.register("privacy", views.PrivacySettingViewSet, basename="privacy-setting")

urlpatterns = router.urls + [
    # Feature 19 — Privacy & Accessibility
    path("center/", views_extra.PrivacyCenterView.as_view(), name="privacy-center"),
    path("consent/update/", views_extra.ConsentUpdateView.as_view(), name="consent-update"),
    path("consent/history/", views_extra.ConsentHistoryView.as_view(), name="consent-history"),
    path("visibility/", views_extra.VisibilityControlsView.as_view(), name="visibility-controls"),
    path("contact-controls/", views_extra.EmployerContactControlsView.as_view(), name="contact-controls"),
    path("data-export/", views_extra.DataExportRequestView.as_view(), name="data-export-v2"),
    path("data-deletion/", views_extra.DataDeletionRequestView.as_view(), name="data-deletion-v2"),
    path("accessibility/", views_extra.AccessibilityPreferencesView.as_view(), name="accessibility-prefs"),
    path("help-center/", views_extra.HelpCenterContentView.as_view(), name="help-center"),
    path("account-safety/", views_extra.AccountSafetyStatusView.as_view(), name="account-safety"),
]
