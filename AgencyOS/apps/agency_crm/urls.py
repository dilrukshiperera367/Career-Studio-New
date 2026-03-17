"""Agency CRM URL configuration."""
from rest_framework.routers import DefaultRouter
from .views import (
    ProspectCompanyViewSet, ClientAccountViewSet, ClientContactViewSet,
    OpportunityViewSet, ActivityLogViewSet, RateCardViewSet, AccountPlanViewSet,
)

router = DefaultRouter()
router.register("prospects", ProspectCompanyViewSet, basename="prospect")
router.register("client-accounts", ClientAccountViewSet, basename="client-account")
router.register("contacts", ClientContactViewSet, basename="contact")
router.register("opportunities", OpportunityViewSet, basename="opportunity")
router.register("activities", ActivityLogViewSet, basename="activity")
router.register("rate-cards", RateCardViewSet, basename="rate-card")
router.register("account-plans", AccountPlanViewSet, basename="account-plan")

urlpatterns = router.urls
