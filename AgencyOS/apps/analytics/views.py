from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from apps.agencies.models import (
    Agency, AgencySubmission, AgencyPlacement, AgencyContractor, AgencyJobOrder
)


class AgencyAnalyticsView(APIView):
    """Agency-level analytics and KPIs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.query_params.get("agency_id")
        period_days = int(request.query_params.get("period_days", 30))
        since = timezone.now() - timedelta(days=period_days)

        agency_qs = Agency.objects.filter(
            Q(owner=request.user) | Q(recruiters__user=request.user)
        ).distinct()

        if agency_id:
            agency_qs = agency_qs.filter(id=agency_id)

        agency_ids = list(agency_qs.values_list("id", flat=True))

        submissions = AgencySubmission.objects.filter(agency_id__in=agency_ids)
        placements = AgencyPlacement.objects.filter(submission__agency_id__in=agency_ids)
        contractors = AgencyContractor.objects.filter(agency_id__in=agency_ids)
        orders = AgencyJobOrder.objects.filter(agency_id__in=agency_ids)

        conversion_rate = 0
        total_subs = submissions.count()
        if total_subs > 0:
            placed_count = submissions.filter(status="placed").count()
            conversion_rate = round((placed_count / total_subs) * 100, 1)

        avg_fee = placements.aggregate(avg=Sum("fee_amount"))["avg"] or 0
        placement_count = placements.count()
        if placement_count > 0:
            avg_fee = round(float(avg_fee) / placement_count, 2)

        return Response({
            "period_days": period_days,
            "submissions": {
                "total": total_subs,
                "this_period": submissions.filter(created_at__gte=since).count(),
                "by_status": dict(
                    submissions.values_list("status").annotate(count=Count("id"))
                    .values_list("status", "count")
                ),
            },
            "placements": {
                "total": placement_count,
                "this_period": placements.filter(created_at__gte=since).count(),
                "fees_collected": float(placements.filter(fee_paid=True).aggregate(total=Sum("fee_amount"))["total"] or 0),
                "fees_pending": float(placements.filter(fee_paid=False).aggregate(total=Sum("fee_amount"))["total"] or 0),
                "avg_fee": avg_fee,
            },
            "contractors": {
                "total": contractors.count(),
                "available": contractors.filter(status="available").count(),
                "on_assignment": contractors.filter(status="on_assignment").count(),
            },
            "job_orders": {
                "open": orders.filter(status="open").count(),
                "in_progress": orders.filter(status="in_progress").count(),
                "filled": orders.filter(status="filled").count(),
            },
            "conversion_rate_percent": conversion_rate,
        })
