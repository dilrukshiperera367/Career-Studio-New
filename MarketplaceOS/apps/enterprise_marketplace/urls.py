from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnterpriseAccountViewSet, EnterpriseTeamMemberViewSet, EnterpriseBudgetViewSet,
    EnterpriseApprovedProviderViewSet, EnterpriseCatalogViewSet,
    EnterpriseBookingApprovalViewSet, InternalMentorProgramViewSet, InternalMentorMatchViewSet,
)

router = DefaultRouter()
router.register("enterprise-accounts", EnterpriseAccountViewSet, basename="enterprise-account")
router.register("enterprise-members", EnterpriseTeamMemberViewSet, basename="enterprise-member")
router.register("enterprise-budgets", EnterpriseBudgetViewSet, basename="enterprise-budget")
router.register("enterprise-approved-providers", EnterpriseApprovedProviderViewSet, basename="enterprise-approved-provider")
router.register("enterprise-catalog", EnterpriseCatalogViewSet, basename="enterprise-catalog")
router.register("enterprise-approvals", EnterpriseBookingApprovalViewSet, basename="enterprise-approval")
router.register("internal-mentor-programs", InternalMentorProgramViewSet, basename="internal-mentor-program")
router.register("internal-mentor-matches", InternalMentorMatchViewSet, basename="internal-mentor-match")

urlpatterns = [path("", include(router.urls))]
