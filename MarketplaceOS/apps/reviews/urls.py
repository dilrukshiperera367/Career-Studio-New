from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet, ProviderResponseViewSet, ReviewFlagViewSet, OutcomeTagViewSet, ReviewSummaryViewSet

router = DefaultRouter()
router.register("reviews", ReviewViewSet, basename="review")
router.register("provider-responses", ProviderResponseViewSet, basename="provider-response")
router.register("review-flags", ReviewFlagViewSet, basename="review-flag")
router.register("outcome-tags", OutcomeTagViewSet, basename="outcome-tag")
router.register("review-summaries", ReviewSummaryViewSet, basename="review-summary")

urlpatterns = [path("", include(router.urls))]
