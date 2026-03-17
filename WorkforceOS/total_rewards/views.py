"""
Total Rewards — ViewSets for compensation bands, merit cycles, merit recommendations,
equity grants, total rewards statements, and pay equity analyses.
"""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    CompensationBand,
    MeritCycle,
    MeritRecommendation,
    EquityGrant,
    TotalRewardsStatement,
    PayEquityAnalysis,
    BonusIncentivePlan,
    BonusIncentiveEntry,
    ManagerCompReviewWorkspace,
    CompChangeApproval,
)


# ─── Serializers ────────────────────────────────────────────────────────────

class CompensationBandSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    spread = serializers.ReadOnlyField()

    class Meta:
        model = CompensationBand
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class MeritCycleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = MeritCycle
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class MeritRecommendationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    recommender_name = serializers.SerializerMethodField()
    cycle_name = serializers.SerializerMethodField()

    class Meta:
        model = MeritRecommendation
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'compa_ratio')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None

    def get_recommender_name(self, obj):
        return obj.recommender.full_name if obj.recommender else None

    def get_cycle_name(self, obj):
        return obj.cycle.name if obj.cycle else None


class EquityGrantSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = EquityGrant
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class TotalRewardsStatementSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = TotalRewardsStatement
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'generated_at', 'total_compensation')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class PayEquityAnalysisSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PayEquityAnalysis
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ─── ViewSets ───────────────────────────────────────────────────────────────

class CompensationBandViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CompensationBandSerializer
    permission_codename = 'total_rewards.manage_comp_bands'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['grade', 'band', 'is_active']
    search_fields = ['name', 'job_family']
    ordering_fields = ['grade', 'band', 'name', 'min_salary', 'max_salary', 'effective_date']

    def get_queryset(self):
        return CompensationBand.objects.filter(tenant_id=self.request.tenant_id)


class MeritCycleViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = MeritCycleSerializer
    permission_codename = 'total_rewards.manage_merit_cycles'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['cycle_year', 'status']
    ordering_fields = ['cycle_year', 'effective_date', 'created_at']

    def get_queryset(self):
        return MeritCycle.objects.filter(tenant_id=self.request.tenant_id)


class MeritRecommendationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = MeritRecommendationSerializer
    permission_codename = 'total_rewards.manage_merit_recommendations'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['cycle', 'employee', 'status', 'recommender']
    ordering_fields = ['created_at', 'updated_at', 'merit_increase_pct', 'bonus_amount']

    def get_queryset(self):
        return MeritRecommendation.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('cycle', 'employee', 'recommender')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        """Submit a merit recommendation for calibration."""
        recommendation = self.get_object()
        recommendation.status = 'submitted'
        recommendation.save(update_fields=['status'])
        return Response(self.get_serializer(recommendation).data)


class EquityGrantViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EquityGrantSerializer
    permission_codename = 'total_rewards.manage_equity'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'grant_type', 'status']
    ordering_fields = ['grant_date', 'created_at', 'units_granted']

    def get_queryset(self):
        return EquityGrant.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')


class TotalRewardsStatementViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TotalRewardsStatementSerializer
    permission_codename = 'total_rewards.view_trs'
    http_method_names = ['get', 'head', 'options']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'statement_year']
    ordering_fields = ['statement_year', 'generated_at', 'total_compensation']

    def get_queryset(self):
        return TotalRewardsStatement.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get'], url_path='my-statements')
    def my_statements(self, request):
        """Return all total rewards statements for the current employee."""
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response([])

        qs = self.get_queryset().filter(
            employee=employee,
            is_visible_to_employee=True,
        ).order_by('-statement_year')

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class PayEquityAnalysisViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PayEquityAnalysisSerializer
    permission_codename = 'total_rewards.manage_pay_equity'
    http_method_names = ['get', 'head', 'options']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['analysis_type']
    ordering_fields = ['analysis_date', 'created_at', 'gap_pct', 'risk_level']

    def get_queryset(self):
        return PayEquityAnalysis.objects.filter(tenant_id=self.request.tenant_id)


# ============ FEATURE 5: BONUS, INCENTIVE & COMP REVIEW VIEWSETS ============

class BonusIncentivePlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = BonusIncentivePlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class BonusIncentivePlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BonusIncentivePlanSerializer
    permission_codename = 'total_rewards.manage_bonus_plans'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['plan_type', 'plan_year', 'is_active']
    ordering_fields = ['plan_year', 'name', 'created_at']

    def get_queryset(self):
        return BonusIncentivePlan.objects.filter(tenant_id=self.request.tenant_id)


class BonusIncentiveEntrySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = BonusIncentiveEntry
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else None


class BonusIncentiveEntryViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BonusIncentiveEntrySerializer
    permission_codename = 'total_rewards.manage_bonus_entries'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['plan', 'employee', 'status']
    ordering_fields = ['created_at', 'awarded_amount']

    def get_queryset(self):
        return BonusIncentiveEntry.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('plan', 'employee')


class ManagerCompReviewWorkspaceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()
    cycle_name = serializers.SerializerMethodField()

    class Meta:
        model = ManagerCompReviewWorkspace
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_manager_name(self, obj):
        return obj.manager.full_name if obj.manager else None

    def get_cycle_name(self, obj):
        return obj.cycle.name if obj.cycle else None


class ManagerCompReviewWorkspaceViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ManagerCompReviewWorkspaceSerializer
    permission_codename = 'total_rewards.manage_comp_review'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['cycle', 'manager', 'status']
    ordering_fields = ['created_at', 'submitted_at']

    def get_queryset(self):
        return ManagerCompReviewWorkspace.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('cycle', 'manager')


class CompChangeApprovalSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = CompChangeApproval
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class CompChangeApprovalViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CompChangeApprovalSerializer
    permission_codename = 'total_rewards.manage_comp_approvals'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'approver', 'status', 'approval_level']
    ordering_fields = ['created_at', 'decided_at', 'approval_level']

    def get_queryset(self):
        return CompChangeApproval.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'approver')
