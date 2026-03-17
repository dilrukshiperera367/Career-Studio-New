"""Workflow Automation API — Definition CRUD, execution history, trigger test."""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from .models import WorkflowDefinition, WorkflowExecution


# --- Serializers ---

class WorkflowDefinitionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    execution_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowDefinition
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'run_count', 'last_run_at', 'created_at', 'updated_at']

    def get_execution_count(self, obj):
        return obj.executions.count()


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = '__all__'
        read_only_fields = '__all__'


# --- Views ---

class WorkflowDefinitionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = WorkflowDefinition.objects.all()
    serializer_class = WorkflowDefinitionSerializer
    filterset_fields = ['is_active', 'trigger_event', 'is_template']
    search_fields = ['name', 'description']

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        workflow = self.get_object()
        workflow.is_active = not workflow.is_active
        workflow.save(update_fields=['is_active', 'updated_at'])
        return Response({'data': WorkflowDefinitionSerializer(workflow).data})

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Dry-run a workflow with test data."""
        workflow = self.get_object()
        test_data = request.data.get('trigger_data', {})
        execution = WorkflowExecution.objects.create(
            tenant=workflow.tenant, workflow=workflow,
            trigger_event=workflow.trigger_event, trigger_data=test_data,
            status='completed', actions_executed=[
                {'action': a.get('type', 'unknown'), 'status': 'simulated'}
                for a in workflow.actions
            ],
            completed_at=timezone.now())
        workflow.run_count += 1
        workflow.last_run_at = timezone.now()
        workflow.save(update_fields=['run_count', 'last_run_at'])
        return Response({'data': WorkflowExecutionSerializer(execution).data})

    @action(detail=False, methods=['get'])
    def templates(self, request):
        templates = self.get_queryset().filter(is_template=True)
        return Response({'data': WorkflowDefinitionSerializer(templates, many=True).data})

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        workflow = self.get_object()
        executions = workflow.executions.all()[:50]
        return Response({'data': WorkflowExecutionSerializer(executions, many=True).data})


class WorkflowExecutionViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = WorkflowExecution.objects.select_related('workflow').all()
    serializer_class = WorkflowExecutionSerializer
    filterset_fields = ['workflow', 'status']
    ordering_fields = ['started_at']
