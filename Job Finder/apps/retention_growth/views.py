"""Retention Growth — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from apps.jobs.serializers import JobListSerializer
from .models import DigestQueue, InactivityRecord


class NewSinceLastVisitView(APIView):
    """Return new jobs posted since the user's last login/visit."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            inactivity = InactivityRecord.objects.get(user=request.user)
            since = inactivity.last_login_at or inactivity.last_search_at
        except InactivityRecord.DoesNotExist:
            since = None

        qs = JobListing.objects.filter(status="active").select_related("employer", "district", "category")
        if since:
            qs = qs.filter(published_at__gte=since)
        qs = qs.order_by("-published_at")[:20]
        return Response({
            "since": since.isoformat() if since else None,
            "count": qs.count(),
            "results": JobListSerializer(qs, many=True, context={"request": request}).data,
        })


class DigestPreviewView(APIView):
    """Preview digest email content for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        digest = DigestQueue.objects.filter(user=request.user, is_sent=False).first()
        if not digest:
            # Generate a basic digest preview from current best matches
            jobs = JobListing.objects.filter(status="active").order_by("-published_at")[:8]
            return Response({
                "type": "weekly",
                "job_count": jobs.count(),
                "jobs": JobListSerializer(jobs, many=True, context={"request": request}).data,
            })
        jobs_qs = JobListing.objects.filter(pk__in=digest.job_ids, status="active")
        return Response({
            "type": digest.digest_type,
            "scheduled_for": digest.scheduled_for.isoformat(),
            "job_count": len(digest.job_ids),
            "jobs": JobListSerializer(jobs_qs, many=True, context={"request": request}).data,
        })
