"""Marketplace Analytics — views."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MarketplaceLiquiditySnapshot, FunnelEvent, EmployerROISummary, MarketplaceHealthScore
from .serializers import LiquiditySnapshotSerializer, EmployerROISummarySerializer, MarketplaceHealthSerializer


class MarketplaceLiquidityView(APIView):
    """Supply vs demand by category/district (admin)."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        category_id = request.query_params.get("category")
        district_id = request.query_params.get("district")
        qs = MarketplaceLiquiditySnapshot.objects.all().select_related("category", "district")
        if category_id:
            qs = qs.filter(category_id=category_id)
        if district_id:
            qs = qs.filter(district_id=district_id)
        qs = qs[:90]
        return Response(LiquiditySnapshotSerializer(qs, many=True).data)


class FunnelStatsView(APIView):
    """Search-to-apply funnel statistics (admin)."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        last_30 = timezone.now() - timedelta(days=30)
        stats = (
            FunnelEvent.objects.filter(created_at__gte=last_30)
            .values("step")
            .annotate(count=Count("id"))
            .order_by("step")
        )
        return Response(list(stats))


class EmployerROIView(APIView):
    """Employer ROI dashboard — for employer or admin."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, employer_id=None):
        if employer_id and request.user.is_staff:
            target_id = employer_id
        else:
            m = request.user.employer_memberships.filter(role__in=["owner", "admin"]).values_list("employer", flat=True).first()
            target_id = m
        if not target_id:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        summaries = EmployerROISummary.objects.filter(employer_id=target_id).order_by("-week_start")[:12]
        return Response(EmployerROISummarySerializer(summaries, many=True).data)


class MarketplaceHealthView(APIView):
    """Marketplace health scores (admin)."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        scores = MarketplaceHealthScore.objects.all()[:30]
        return Response(MarketplaceHealthSerializer(scores, many=True).data)

    def get_latest(self, request):
        score = MarketplaceHealthScore.objects.first()
        if not score:
            return Response({"detail": "No data yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MarketplaceHealthSerializer(score).data)
