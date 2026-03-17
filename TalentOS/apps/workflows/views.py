"""API views for workflow management."""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import AutomationRule, WorkflowExecution
from .serializers import WorkflowRuleSerializer, WorkflowExecutionSerializer
from .services import process_event


class WorkflowRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = WorkflowRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        qs = AutomationRule.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by("-created_at")


class WorkflowRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WorkflowRuleSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        qs = AutomationRule.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_rule(request, pk):
    """Toggle a workflow rule on/off."""
    try:
        rule = AutomationRule.objects.get(pk=pk)
        rule.enabled = not rule.enabled
        rule.save(update_fields=["enabled"])
        return Response({"id": str(rule.id), "enabled": rule.enabled})
    except AutomationRule.DoesNotExist:
        return Response({"error": "Rule not found"}, status=404)


class WorkflowExecutionListView(generics.ListAPIView):
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        qs = WorkflowExecution.objects.all()
        if tenant:
            qs = qs.filter(rule__tenant=tenant)
        return qs.select_related("rule").order_by("-executed_at")[:100]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trigger_workflow(request):
    """Manually trigger a workflow rule.
    POST { "rule_id": "...", "context": {...} }
    """
    rule_id = request.data.get("rule_id")
    context = request.data.get("context", {})
    try:
        rule = AutomationRule.objects.get(id=rule_id)
        result = process_event({"rule_id": str(rule.id), **context})
        return Response({"status": "executed", "result": str(result)})
    except AutomationRule.DoesNotExist:
        return Response({"error": "Rule not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
