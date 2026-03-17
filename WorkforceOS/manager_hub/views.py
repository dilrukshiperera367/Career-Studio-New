"""
Manager Hub — ViewSets for manager dashboard, team management, 1:1s, coaching, and approvals.
"""

from django.utils import timezone
from django.db.models import Avg, Count, Q
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    ManagerDashboardConfig, TeamAlert, OneOnOne,
    CoachingNote, TeamPerformanceSummary, DelegationRule,
    TeamRosterView, TeamAttendanceSnapshot, ApprovalItem,
    OnboardingOffboardingTracker, SkillGapSummary, FlightRiskAlert,
    SuccessionPlanEntry, CompPlanningWorkspace, RecognitionAction,
    TrainingCompletionView, WorkforceCostSnapshot, ScheduleCoverageAlert,
    ActionRecommendation,
)


# ─── Serializers ────────────────────────────────────────────────────────────

class ManagerDashboardConfigSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ManagerDashboardConfig
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class TeamAlertSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = TeamAlert
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class OneOnOneSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = OneOnOne
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_manager_name(self, obj):
        return obj.manager.full_name

    def get_employee_name(self, obj):
        return obj.employee.full_name


class CoachingNoteSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CoachingNote
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class TeamPerformanceSummarySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TeamPerformanceSummary
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class DelegationRuleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = DelegationRule
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ─── ViewSets ───────────────────────────────────────────────────────────────

class ManagerDashboardConfigViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ManagerDashboardConfigSerializer
    permission_codename = 'manager_hub.manage_dashboard'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['manager']

    def get_queryset(self):
        return ManagerDashboardConfig.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get', 'patch'], url_path='my')
    def my_config(self, request):
        """Get or update the current manager's dashboard config."""
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response({'detail': 'No employee profile found.'}, status=status.HTTP_404_NOT_FOUND)

        config, _ = ManagerDashboardConfig.objects.get_or_create(
            manager=employee, tenant_id=request.tenant_id
        )
        if request.method == 'PATCH':
            serializer = self.get_serializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(config).data)


class TeamAlertViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TeamAlertSerializer
    permission_codename = 'manager_hub.view_team_alerts'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'alert_type', 'severity', 'is_dismissed']
    ordering_fields = ['created_at', 'severity', 'due_date']

    def get_queryset(self):
        return TeamAlert.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        alert = self.get_object()
        alert.is_dismissed = True
        alert.dismissed_at = timezone.now()
        alert.save(update_fields=['is_dismissed', 'dismissed_at'])
        return Response({'status': 'dismissed'})

    @action(detail=False, methods=['get'], url_path='my-alerts')
    def my_alerts(self, request):
        """Return undismissed alerts for the current manager."""
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response([])
        qs = self.get_queryset().filter(manager=employee, is_dismissed=False).order_by('-created_at')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class OneOnOneViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = OneOnOneSerializer
    permission_codename = 'manager_hub.manage_one_on_ones'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'status', 'recurrence']
    search_fields = ['agenda', 'notes']
    ordering_fields = ['scheduled_at', 'created_at']

    def get_queryset(self):
        return OneOnOne.objects.filter(tenant_id=self.request.tenant_id).select_related('manager', 'employee')

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        one_on_one = self.get_object()
        one_on_one.status = 'completed'
        one_on_one.completed_at = timezone.now()
        if 'notes' in request.data:
            one_on_one.notes = request.data['notes']
        if 'action_items' in request.data:
            one_on_one.action_items = request.data['action_items']
        one_on_one.save()
        return Response(self.get_serializer(one_on_one).data)

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """Return next 10 upcoming 1:1s for the current user."""
        now = timezone.now()
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response([])
        qs = self.get_queryset().filter(
            Q(manager=employee) | Q(employee=employee),
            scheduled_at__gte=now,
            status='scheduled'
        ).order_by('scheduled_at')[:10]
        return Response(self.get_serializer(qs, many=True).data)


class CoachingNoteViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CoachingNoteSerializer
    permission_codename = 'manager_hub.manage_coaching_notes'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'note_type', 'is_shared_with_hr']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return CoachingNote.objects.filter(tenant_id=self.request.tenant_id)


class TeamPerformanceSummaryViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TeamPerformanceSummarySerializer
    permission_codename = 'manager_hub.view_team_performance'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'period_year', 'period_month']
    ordering_fields = ['period_year', 'period_month']
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return TeamPerformanceSummary.objects.filter(tenant_id=self.request.tenant_id)


class DelegationRuleViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = DelegationRuleSerializer
    permission_codename = 'manager_hub.manage_delegations'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['delegator', 'delegate', 'is_active']
    ordering_fields = ['start_date', 'end_date']

    def get_queryset(self):
        return DelegationRule.objects.filter(tenant_id=self.request.tenant_id).select_related('delegator', 'delegate')


# ─── Feature 3 New Serializers ───────────────────────────────────────────────

class TeamRosterViewSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TeamRosterView
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class TeamAttendanceSnapshotSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TeamAttendanceSnapshot
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class ApprovalItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class OnboardingOffboardingTrackerSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingOffboardingTracker
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'last_refreshed_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class SkillGapSummarySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SkillGapSummary
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class FlightRiskAlertSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = FlightRiskAlert
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'generated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class SuccessionPlanEntrySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    successor_name = serializers.SerializerMethodField()

    class Meta:
        model = SuccessionPlanEntry
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_successor_name(self, obj):
        return obj.successor.full_name if obj.successor else None


class CompPlanningWorkspaceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CompPlanningWorkspace
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class RecognitionActionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = RecognitionAction
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class TrainingCompletionViewSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TrainingCompletionView
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class WorkforceCostSnapshotSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = WorkforceCostSnapshot
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'computed_at')


class ScheduleCoverageAlertSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ScheduleCoverageAlert
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class ActionRecommendationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ActionRecommendation
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'generated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


# ─── Feature 3 New ViewSets ──────────────────────────────────────────────────

class TeamRosterViewViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TeamRosterViewSerializer
    permission_codename = 'manager_hub.view_team_roster'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['manager', 'include_indirect']

    def get_queryset(self):
        return TeamRosterView.objects.filter(tenant_id=self.request.tenant_id)


class TeamAttendanceSnapshotViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TeamAttendanceSnapshotSerializer
    permission_codename = 'manager_hub.view_team_attendance'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'period_type']
    ordering_fields = ['period_start']

    def get_queryset(self):
        return TeamAttendanceSnapshot.objects.filter(tenant_id=self.request.tenant_id)


class ApprovalItemViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ApprovalItemSerializer
    permission_codename = 'manager_hub.manage_approvals'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['approver', 'employee', 'item_type', 'status', 'priority']
    ordering_fields = ['created_at', 'due_date', 'priority']

    def get_queryset(self):
        return ApprovalItem.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='decide')
    def decide(self, request, pk=None):
        item = self.get_object()
        decision = request.data.get('decision')
        if decision not in ('approved', 'rejected', 'delegated', 'escalated'):
            return Response({'detail': 'Invalid decision.'}, status=status.HTTP_400_BAD_REQUEST)
        item.status = decision
        item.decided_at = timezone.now()
        item.decision_notes = request.data.get('notes', '')
        item.save(update_fields=['status', 'decided_at', 'decision_notes', 'updated_at'])
        return Response(self.get_serializer(item).data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response([])
        qs = self.get_queryset().filter(approver=employee, status='pending').order_by('due_date', '-created_at')
        return Response(self.get_serializer(qs, many=True).data)


class OnboardingOffboardingTrackerViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = OnboardingOffboardingTrackerSerializer
    permission_codename = 'manager_hub.view_ob_ob_tracker'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'tracker_type', 'status']
    ordering_fields = ['target_date']

    def get_queryset(self):
        return OnboardingOffboardingTracker.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')


class SkillGapSummaryViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = SkillGapSummarySerializer
    permission_codename = 'manager_hub.view_skill_gaps'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager']
    ordering_fields = ['analysis_date']

    def get_queryset(self):
        return SkillGapSummary.objects.filter(tenant_id=self.request.tenant_id)


class FlightRiskAlertViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = FlightRiskAlertSerializer
    permission_codename = 'manager_hub.view_flight_risks'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'risk_level', 'is_acknowledged']
    ordering_fields = ['risk_score', 'generated_at']

    def get_queryset(self):
        return FlightRiskAlert.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.acknowledged_at = timezone.now()
        alert.action_taken = request.data.get('action_taken', '')
        alert.save(update_fields=['is_acknowledged', 'acknowledged_at', 'action_taken'])
        return Response(self.get_serializer(alert).data)


class SuccessionPlanEntryViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = SuccessionPlanEntrySerializer
    permission_codename = 'manager_hub.manage_succession'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'readiness', 'retention_risk']
    ordering_fields = ['bench_rank', 'created_at']

    def get_queryset(self):
        return SuccessionPlanEntry.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('successor', 'target_role_employee')


class CompPlanningWorkspaceViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CompPlanningWorkspaceSerializer
    permission_codename = 'manager_hub.manage_comp_planning'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'status']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return CompPlanningWorkspace.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        workspace = self.get_object()
        workspace.status = 'submitted'
        workspace.submitted_at = timezone.now()
        workspace.save(update_fields=['status', 'submitted_at', 'updated_at'])
        return Response(self.get_serializer(workspace).data)


class RecognitionActionViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = RecognitionActionSerializer
    permission_codename = 'manager_hub.manage_recognition'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'action_type', 'is_public']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return RecognitionAction.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'manager')


class TrainingCompletionViewViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TrainingCompletionViewSerializer
    permission_codename = 'manager_hub.view_training_compliance'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['manager', 'period_label']

    def get_queryset(self):
        return TrainingCompletionView.objects.filter(tenant_id=self.request.tenant_id)


class WorkforceCostSnapshotViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = WorkforceCostSnapshotSerializer
    permission_codename = 'manager_hub.view_workforce_cost'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'period_year', 'period_month']
    ordering_fields = ['period_year', 'period_month']
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return WorkforceCostSnapshot.objects.filter(tenant_id=self.request.tenant_id)


class ScheduleCoverageAlertViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ScheduleCoverageAlertSerializer
    permission_codename = 'manager_hub.view_schedule_coverage'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'alert_type', 'severity', 'is_resolved']
    ordering_fields = ['created_at', 'affected_date']

    def get_queryset(self):
        return ScheduleCoverageAlert.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['is_resolved', 'resolved_at'])
        return Response(self.get_serializer(alert).data)


class ActionRecommendationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ActionRecommendationSerializer
    permission_codename = 'manager_hub.view_recommendations'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['manager', 'employee', 'category', 'is_dismissed', 'is_actioned']
    ordering_fields = ['priority_score', 'generated_at']

    def get_queryset(self):
        return ActionRecommendation.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        rec = self.get_object()
        rec.is_dismissed = True
        rec.save(update_fields=['is_dismissed'])
        return Response({'status': 'dismissed'})

    @action(detail=True, methods=['post'], url_path='action')
    def mark_actioned(self, request, pk=None):
        rec = self.get_object()
        rec.is_actioned = True
        rec.actioned_at = timezone.now()
        rec.save(update_fields=['is_actioned', 'actioned_at'])
        return Response(self.get_serializer(rec).data)
