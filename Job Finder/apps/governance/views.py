"""AI Governance views."""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Q

from .models import AIDecisionLog, BiasMetric, Guardrail
from .serializers import (
    AIDecisionLogSerializer, BiasMetricSerializer, GuardrailSerializer,
)


class DashboardStatsView(APIView):
    """Aggregated stats for the AI governance dashboard."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total = AIDecisionLog.objects.count()
        reviewed = AIDecisionLog.objects.filter(is_reviewed=True).count()
        pending = AIDecisionLog.objects.filter(is_reviewed=False).count()
        violations = BiasMetric.objects.filter(status="fail").count()
        return Response({
            "total_decisions": total,
            "reviewed": reviewed,
            "pending_review": pending,
            "violations": violations,
        })


class AIDecisionLogListView(generics.ListCreateAPIView):
    serializer_class = AIDecisionLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AIDecisionLog.objects.all()
        decision_type = self.request.query_params.get("type")
        reviewed = self.request.query_params.get("reviewed")
        if decision_type:
            qs = qs.filter(decision_type=decision_type)
        if reviewed == "true":
            qs = qs.filter(is_reviewed=True)
        elif reviewed == "false":
            qs = qs.filter(is_reviewed=False)
        return qs


class AIDecisionLogDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AIDecisionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AIDecisionLog.objects.all()


class AIDecisionReviewView(APIView):
    """Mark a decision as reviewed."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            log = AIDecisionLog.objects.get(pk=pk)
        except AIDecisionLog.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        log.is_reviewed = True
        log.reviewer = request.data.get("reviewer", str(request.user))
        log.reviewed_at = timezone.now()
        log.save()
        return Response(AIDecisionLogSerializer(log).data)


class BiasMetricListView(generics.ListCreateAPIView):
    serializer_class = BiasMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = BiasMetric.objects.all()


class GuardrailListView(generics.ListCreateAPIView):
    serializer_class = GuardrailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Guardrail.objects.all()


class GuardrailToggleView(APIView):
    """Toggle a guardrail on/off."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            guardrail = Guardrail.objects.get(pk=pk)
        except Guardrail.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        guardrail.is_active = not guardrail.is_active
        guardrail.save()
        return Response(GuardrailSerializer(guardrail).data)
