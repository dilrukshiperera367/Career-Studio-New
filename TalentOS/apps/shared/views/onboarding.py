"""Onboarding views — buddy suggestions and early attrition checks for new hires."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasTenantAccess


class EarlyAttritionView(APIView):
    """Employees who left within 90 days."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.candidates.utils import check_early_attrition
        return Response({"alerts": check_early_attrition(request.tenant_id)})


class BuddySuggestionView(APIView):
    """Auto-suggest buddy/mentor for new hire."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request, pk):
        from apps.candidates.utils import suggest_buddy
        return Response({"suggestions": suggest_buddy(request.tenant_id, str(pk))})
