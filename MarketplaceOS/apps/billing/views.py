from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    ProviderPlan, ProviderSubscription, MarketplaceCommissionConfig,
    BookingCommission, CourseCommission, FeaturedListingProduct, FeaturedListingPurchase,
    EnterpriseBudget, EnterpriseBudgetTransaction, CoachingBundle,
)
from .serializers import (
    ProviderPlanSerializer, ProviderSubscriptionSerializer,
    MarketplaceCommissionConfigSerializer, BookingCommissionSerializer,
    CourseCommissionSerializer, FeaturedListingProductSerializer,
    FeaturedListingPurchaseSerializer, EnterpriseBudgetSerializer,
    EnterpriseBudgetTransactionSerializer, CoachingBundleSerializer,
)


class ProviderPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProviderPlan.objects.all()
    serializer_class = ProviderPlanSerializer
    permission_classes = [permissions.AllowAny]


class ProviderSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ProviderSubscription.objects.select_related("provider", "plan").all()
        try:
            provider = user.provider_profile
            return ProviderSubscription.objects.filter(provider=provider)
        except Exception:
            return ProviderSubscription.objects.none()

    @action(detail=False, methods=["get"], url_path="my-subscription")
    def my_subscription(self, request):
        try:
            provider = request.user.provider_profile
            subscription = ProviderSubscription.objects.filter(provider=provider, status="active").first()
            if not subscription:
                return Response({"detail": "No active subscription found."}, status=404)
            return Response(ProviderSubscriptionSerializer(subscription).data)
        except Exception:
            return Response({"detail": "Provider profile not found."}, status=404)


class MarketplaceCommissionConfigViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceCommissionConfig.objects.all()
    serializer_class = MarketplaceCommissionConfigSerializer
    permission_classes = [permissions.IsAdminUser]


class BookingCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookingCommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return BookingCommission.objects.all()
        try:
            provider = self.request.user.provider_profile
            return BookingCommission.objects.filter(provider=provider)
        except Exception:
            return BookingCommission.objects.none()


class FeaturedListingProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeaturedListingProduct.objects.filter(is_active=True)
    serializer_class = FeaturedListingProductSerializer
    permission_classes = [permissions.AllowAny]


class FeaturedListingPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = FeaturedListingPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return FeaturedListingPurchase.objects.all()
        try:
            provider = self.request.user.provider_profile
            return FeaturedListingPurchase.objects.filter(provider=provider)
        except Exception:
            return FeaturedListingPurchase.objects.none()


class EnterpriseBudgetViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseBudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return EnterpriseBudget.objects.all()
        # Enterprise admins see their own company budgets
        return EnterpriseBudget.objects.filter(
            enterprise__team_members__user=self.request.user,
            enterprise__team_members__role="admin",
        )


class EnterpriseBudgetTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnterpriseBudgetTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return EnterpriseBudgetTransaction.objects.all()
        budget_id = self.request.query_params.get("budget")
        if budget_id:
            return EnterpriseBudgetTransaction.objects.filter(budget__id=budget_id)
        return EnterpriseBudgetTransaction.objects.none()


class CoachingBundleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CoachingBundle.objects.filter(is_active=True)
    serializer_class = CoachingBundleSerializer
    permission_classes = [permissions.AllowAny]
