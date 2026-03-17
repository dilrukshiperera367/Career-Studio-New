"""Onboarding API views + serializers + URLs."""

from rest_framework import viewsets, serializers, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from config.base_api import TenantViewSetMixin, TenantSerializerMixin, AuditMixin
from platform_core.services import emit_timeline_event, send_notification
from .models import (
    OnboardingTemplate, OnboardingInstance, OnboardingTask, Asset,
    PreboardingPortal, BuddyAssignment, MilestonePlan, MilestonePlanItem,
)


# --- Serializers ---

class OnboardingTemplateSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = OnboardingTemplate
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class OnboardingTaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTask
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_assignee_name(self, obj):
        return obj.assignee.full_name if obj.assignee else None


class OnboardingInstanceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    tasks = OnboardingTaskSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingInstance
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'completion_pct', 'created_at', 'updated_at']


class AssetSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


# --- Views ---

class OnboardingTemplateViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = OnboardingTemplate.objects.all()
    serializer_class = OnboardingTemplateSerializer
    filterset_fields = ['status']


class OnboardingInstanceViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = OnboardingInstance.objects.select_related('employee', 'template').prefetch_related('tasks').all()
    serializer_class = OnboardingInstanceSerializer
    filterset_fields = ['employee', 'status']

    @action(detail=True, methods=['get'], url_path='tasks')
    def list_tasks(self, request, pk=None):
        instance = self.get_object()
        tasks = instance.tasks.all()
        return Response({'data': OnboardingTaskSerializer(tasks, many=True).data})


class OnboardingTaskViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = OnboardingTask.objects.select_related('instance', 'assignee').all()
    serializer_class = OnboardingTaskSerializer
    filterset_fields = ['instance', 'status', 'category', 'assignee']

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.save()
        # Recalculate instance progress
        task.instance.recalculate_progress()

        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=task.instance.employee,
            event_type='onboarding.task_completed',
            category='onboarding',
            title=f'Onboarding task completed: {task.title}',
            actor=request.user,
            source_object_type='OnboardingTask',
            source_object_id=task.id,
        )
        return Response({'data': OnboardingTaskSerializer(task).data})


class AssetViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('assigned_to').all()
    serializer_class = AssetSerializer
    filterset_fields = ['category', 'status', 'assigned_to']
    search_fields = ['name', 'serial_number']


# ===================== EXIT / OFFBOARDING =====================

from .exit_models import ExitRequest, ExitChecklist, ExitInterview


class ExitRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = ExitRequest
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class ExitChecklistSerializer(serializers.ModelSerializer):
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = ExitChecklist
        fields = '__all__'
        read_only_fields = ['id']

    def get_assignee_name(self, obj):
        return obj.assignee.full_name if obj.assignee else None


class ExitInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitInterview
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ExitRequestViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = ExitRequest.objects.select_related('employee', 'approved_by').all()
    serializer_class = ExitRequestSerializer
    filterset_fields = ['exit_type', 'status']
    ordering_fields = ['created_at', 'last_working_date']

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        exit_req = self.get_object()
        exit_req.status = 'accepted'
        exit_req.approved_by = request.user
        exit_req.save()
        return Response({'data': ExitRequestSerializer(exit_req).data})

    @action(detail=True, methods=['post'], url_path='advance')
    def advance_status(self, request, pk=None):
        exit_req = self.get_object()
        pipeline = ['submitted', 'accepted', 'notice_period', 'handover', 'exit_interview', 'settlement', 'completed']
        idx = pipeline.index(exit_req.status) if exit_req.status in pipeline else -1
        if idx < len(pipeline) - 1:
            exit_req.status = pipeline[idx + 1]
            exit_req.save()
        return Response({'data': ExitRequestSerializer(exit_req).data})

    @action(detail=True, methods=['get'])
    def checklist(self, request, pk=None):
        exit_req = self.get_object()
        items = exit_req.checklist_items.all()
        return Response({'data': ExitChecklistSerializer(items, many=True).data})


class ExitChecklistViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExitChecklist.objects.select_related('assignee').all()
    serializer_class = ExitChecklistSerializer
    filterset_fields = ['status', 'category']

    def get_queryset(self):
        return ExitChecklist.objects.select_related('assignee').filter(
            exit_request__tenant_id=self.request.tenant_id
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        item = self.get_object()
        item.status = 'completed'
        item.completed_at = timezone.now()
        item.save()
        return Response({'data': ExitChecklistSerializer(item).data})


class ExitInterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ExitInterview.objects.select_related('exit_request', 'conducted_by').all()
    serializer_class = ExitInterviewSerializer

    def get_queryset(self):
        return ExitInterview.objects.select_related('exit_request', 'conducted_by').filter(
            exit_request__tenant_id=self.request.tenant_id
        )


# =============================================================================
# P1 Upgrades — Preboarding Portal, Buddy Assignment, Milestone Plans
# =============================================================================

class PreboardingPortalSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = PreboardingPortal
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class BuddyAssignmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    new_employee_name = serializers.CharField(source='new_employee.full_name', read_only=True)
    buddy_name = serializers.CharField(source='buddy.full_name', read_only=True)

    class Meta:
        model = BuddyAssignment
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class MilestonePlanItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestonePlanItem
        fields = '__all__'
        read_only_fields = ['id']


class MilestonePlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    items = MilestonePlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = MilestonePlan
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class PreboardingPortalViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PreboardingPortal.objects.select_related('employee').all()
    serializer_class = PreboardingPortalSerializer
    filterset_fields = ['employee', 'status']


class BuddyAssignmentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = BuddyAssignment.objects.select_related('new_employee', 'buddy').all()
    serializer_class = BuddyAssignmentSerializer
    filterset_fields = ['new_employee', 'buddy', 'status']


class MilestonePlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = MilestonePlan.objects.select_related('employee').prefetch_related('items').all()
    serializer_class = MilestonePlanSerializer
    filterset_fields = ['employee', 'status']

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        plan = self.get_object()
        return Response({'data': MilestonePlanItemSerializer(plan.items.all(), many=True).data})


class MilestonePlanItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MilestonePlanItemSerializer
    filterset_fields = ['plan', 'phase', 'status']

    def get_queryset(self):
        return MilestonePlanItem.objects.filter(
            plan__tenant_id=self.request.tenant_id
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        item = self.get_object()
        item.status = 'completed'
        item.completed_at = timezone.now()
        item.save(update_fields=['status', 'completed_at'])
        return Response({'data': MilestonePlanItemSerializer(item).data})

