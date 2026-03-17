from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import datetime
from .models import (
    MarketplaceDailySnapshot, ProviderDailySnapshot,
    SearchEvent, BookingFunnelEvent, ProviderViewEvent, RevenueByCategory,
)
from .serializers import (
    MarketplaceDailySnapshotSerializer, ProviderDailySnapshotSerializer,
    SearchEventSerializer, BookingFunnelEventSerializer,
    ProviderViewEventSerializer,
)


class MarketplaceSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only marketplace KPI snapshots."""
    queryset = MarketplaceDailySnapshot.objects.all()
    serializer_class = MarketplaceDailySnapshotSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        days = self.request.query_params.get("days", 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
        cutoff = timezone.now().date() - datetime.timedelta(days=days)
        return qs.filter(date__gte=cutoff)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Return latest 7-day and 30-day aggregates."""
        today = timezone.now().date()
        last_7 = MarketplaceDailySnapshot.objects.filter(
            date__gte=today - datetime.timedelta(days=7)
        )
        last_30 = MarketplaceDailySnapshot.objects.filter(
            date__gte=today - datetime.timedelta(days=30)
        )
        from django.db.models import Sum, Avg

        def agg(qs):
            return qs.aggregate(
                gmv=Sum("gross_merchandise_value_lkr"),
                commission=Sum("platform_commission_lkr"),
                bookings=Sum("total_bookings"),
                completed=Sum("completed_bookings"),
                avg_aov=Avg("average_order_value_lkr"),
            )

        return Response({
            "last_7_days": agg(last_7),
            "last_30_days": agg(last_30),
        })


class ProviderAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """Provider sees their own analytics snapshots."""
    serializer_class = ProviderDailySnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            provider = user.provider_profile
        except Exception:
            return ProviderDailySnapshot.objects.none()
        days = self.request.query_params.get("days", 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
        cutoff = timezone.now().date() - datetime.timedelta(days=days)
        return ProviderDailySnapshot.objects.filter(provider=provider, date__gte=cutoff)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        from django.db.models import Sum, Avg
        qs = self.get_queryset()
        data = qs.aggregate(
            total_earnings=Sum("earnings_lkr"),
            total_bookings=Sum("bookings_received"),
            total_completed=Sum("bookings_completed"),
            avg_rating=Avg("avg_rating"),
            total_views=Sum("profile_views"),
        )
        return Response(data)


class SearchEventViewSet(viewsets.ModelViewSet):
    """
    POST from frontend to log search events.
    GET is admin-only for analytics.
    """
    serializer_class = SearchEventSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return SearchEvent.objects.all()
        return SearchEvent.objects.none()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class BookingFunnelEventViewSet(viewsets.ModelViewSet):
    """POST from frontend to log funnel events."""
    serializer_class = BookingFunnelEventSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return BookingFunnelEvent.objects.all()
        return BookingFunnelEvent.objects.none()

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class ProviderViewEventViewSet(viewsets.ModelViewSet):
    """POST from frontend to log profile views."""
    serializer_class = ProviderViewEventSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return ProviderViewEvent.objects.all()
        return ProviderViewEvent.objects.none()

    def perform_create(self, serializer):
        viewer = self.request.user if self.request.user.is_authenticated else None
        serializer.save(viewer=viewer)
