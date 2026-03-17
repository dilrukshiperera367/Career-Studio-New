"""Feed Normalization — views."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FeedSource, FeedErrorLog, DispositionSyncRecord, FeedDeduplication
from .serializers import FeedSourceSerializer, FeedErrorLogSerializer, DispositionSyncSerializer


class FeedSourceListView(APIView):
    """List feed sources for the authenticated employer."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_employer(self, request):
        m = request.user.employer_memberships.filter(role__in=["owner", "admin"]).select_related("employer").first()
        return m.employer if m else None

    def get(self, request):
        employer = self._get_employer(request)
        if not employer and not request.user.is_staff:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        if request.user.is_staff and not employer:
            sources = FeedSource.objects.all().select_related("employer")[:100]
        else:
            sources = FeedSource.objects.filter(employer=employer)
        return Response(FeedSourceSerializer(sources, many=True).data)

    def post(self, request):
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = FeedSourceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        source = ser.save(employer=employer)
        return Response(FeedSourceSerializer(source).data, status=status.HTTP_201_CREATED)


class FeedErrorLogListView(APIView):
    """List feed error logs."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        source_id = request.query_params.get("source")
        qs = FeedErrorLog.objects.filter(is_resolved=False)
        if source_id:
            qs = qs.filter(feed_source_id=source_id)
        if not request.user.is_staff:
            employer_id = request.user.employer_memberships.values_list("employer_id", flat=True).first()
            qs = qs.filter(feed_source__employer_id=employer_id)
        return Response(FeedErrorLogSerializer(qs[:100], many=True).data)


class ReplayFeedErrorView(APIView):
    """Retry a failed feed import error."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, error_id):
        try:
            error = FeedErrorLog.objects.get(pk=error_id)
        except FeedErrorLog.DoesNotExist:
            return Response({"detail": "Error not found."}, status=status.HTTP_404_NOT_FOUND)
        if error.retry_count >= error.max_retries:
            return Response(
                {"detail": f"Max retries ({error.max_retries}) reached."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        error.retry_count += 1
        error.next_retry_at = timezone.now()
        error.save(update_fields=["retry_count", "next_retry_at"])
        return Response({
            "queued": True,
            "retry_count": error.retry_count,
            "max_retries": error.max_retries,
        })


class DuplicateDetectionListView(APIView):
    """List detected duplicate jobs from feed normalization."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        dups = FeedDeduplication.objects.filter(was_suppressed=False).select_related("feed_source")[:100]
        data = [
            {
                "id": str(d.id),
                "feed_source": d.feed_source.name,
                "external_id": d.duplicate_external_id,
                "title": d.duplicate_title,
                "similarity": d.similarity_score,
                "detected_at": d.detected_at.isoformat(),
            }
            for d in dups
        ]
        return Response(data)
