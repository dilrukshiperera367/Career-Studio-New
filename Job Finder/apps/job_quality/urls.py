"""Job Quality — URLs."""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("scam-patterns", views.ScamPatternViewSet, basename="scam-patterns")

urlpatterns = [
    path("score/<uuid:job_id>/", views.JobQualityScoreView.as_view(), name="jq-quality-score"),
    path("duplicate-check/<uuid:job_id>/", views.DuplicateCheckView.as_view(), name="jq-duplicate-check"),
    path("scam-risk/<uuid:job_id>/", views.ScamRiskView.as_view(), name="jq-scam-risk"),
] + router.urls
