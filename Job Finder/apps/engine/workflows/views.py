from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import (
    WorkflowDefinition, WorkflowStage, WorkflowInstance,
    WorkflowTask, WorkflowTransition
)
from .serializers import (
    WorkflowDefinitionListSerializer, WorkflowDefinitionDetailSerializer,
    WorkflowStageSerializer, WorkflowInstanceSerializer,
    WorkflowTaskSerializer, WorkflowTransitionSerializer,
    AdvanceWorkflowSerializer
)


class WorkflowDefinitionViewSet(viewsets.ModelViewSet):
    queryset = WorkflowDefinition.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowDefinitionListSerializer
        return WorkflowDefinitionDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_stage(self, request, slug=None):
        workflow = self.get_object()
        serializer = WorkflowStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(workflow=workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorkflowInstanceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WorkflowInstance.objects.select_related(
            'workflow', 'current_stage'
        ).prefetch_related('tasks', 'transitions')

        # Filter by entity
        entity_type = self.request.query_params.get('entity_type')
        entity_id = self.request.query_params.get('entity_id')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)

        # Filter by status
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)

        return qs

    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        """Advance a workflow to the next stage."""
        instance = self.get_object()
        serializer = AdvanceWorkflowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_stage_id = serializer.validated_data['to_stage_id']
        reason = serializer.validated_data.get('reason', '')

        try:
            to_stage = WorkflowStage.objects.get(
                id=to_stage_id, workflow=instance.workflow
            )
        except WorkflowStage.DoesNotExist:
            return Response(
                {'error': 'Invalid stage for this workflow'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create transition record
        WorkflowTransition.objects.create(
            instance=instance,
            from_stage=instance.current_stage,
            to_stage=to_stage,
            triggered_by=request.user,
            trigger_type='manual',
            reason=reason,
        )

        # Update instance
        instance.current_stage = to_stage
        if to_stage.is_terminal:
            instance.status = WorkflowInstance.STATUS_COMPLETED
            instance.completed_at = timezone.now()
        instance.save()

        return Response(WorkflowInstanceSerializer(instance).data)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get all pending tasks assigned to the current user."""
        tasks = WorkflowTask.objects.filter(
            assigned_to=request.user,
            status__in=[WorkflowTask.STATUS_PENDING, WorkflowTask.STATUS_IN_PROGRESS]
        ).select_related('instance__workflow', 'stage').order_by('-priority', 'due_date')
        return Response(WorkflowTaskSerializer(tasks, many=True).data)


class WorkflowTaskViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkflowTask.objects.filter(
            assigned_to=self.request.user
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = WorkflowTask.STATUS_COMPLETED
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.save()
        return Response(WorkflowTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def skip(self, request, pk=None):
        task = self.get_object()
        if task.is_blocking:
            return Response(
                {'error': 'Cannot skip a blocking task'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task.status = WorkflowTask.STATUS_SKIPPED
        task.save()
        return Response(WorkflowTaskSerializer(task).data)
