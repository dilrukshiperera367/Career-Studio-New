"""Miscellaneous views — scheduling conflict detection and other cross-cutting utilities."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasTenantAccess


class InterviewConflictView(APIView):
    """Check if interviewer has scheduling conflicts."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.candidates.utils import check_interview_conflicts
        from datetime import date as d, time as t

        interviewer_id = request.query_params.get("interviewer_id")
        date_str = request.query_params.get("date")
        time_str = request.query_params.get("time")

        if not interviewer_id or not date_str:
            return Response({"error": "interviewer_id and date required"}, status=400)

        try:
            date = d.fromisoformat(date_str)
        except ValueError:
            return Response({"error": "Invalid date format"}, status=400)

        start_time = None
        if time_str:
            try:
                start_time = t.fromisoformat(time_str)
            except ValueError:
                pass

        conflicts = check_interview_conflicts(
            request.tenant_id, interviewer_id, date, start_time
        )
        return Response({"conflicts": conflicts, "has_conflict": len(conflicts) > 0})
