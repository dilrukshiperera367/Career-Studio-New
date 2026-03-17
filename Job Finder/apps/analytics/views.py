"""Analytics views — Platform stats, employer analytics, search logs."""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsAdmin, IsEmployer
from apps.employers.models import EmployerTeamMember
from .models import PlatformStat, EmployerAnalytics, SearchLog
from .serializers import PlatformStatSerializer, EmployerAnalyticsSerializer, DateRangeSerializer


class PlatformStatsView(generics.ListAPIView):
    """Admin-only platform statistics."""
    serializer_class = PlatformStatSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = PlatformStat.objects.all()
        start = self.request.query_params.get("start_date")
        end = self.request.query_params.get("end_date")
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs.order_by("-date")[:90]


class EmployerDashboardAnalyticsView(APIView):
    """Employer dashboard analytics."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get(self, request):
        membership = EmployerTeamMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=404)
        analytics = EmployerAnalytics.objects.filter(
            employer=membership.employer,
        ).order_by("-date")[:30]
        return Response(EmployerAnalyticsSerializer(analytics, many=True).data)


class TopSearchTermsView(APIView):
    """Admin-only top search terms analytics."""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.db.models import Count
        top = SearchLog.objects.filter(
            query__gt="",
        ).values("query").annotate(
            count=Count("id"),
        ).order_by("-count")[:20]
        return Response(list(top))
