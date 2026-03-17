"""
Workforce Planning API views.

Covers all 15 feature areas:
  HeadcountPlan, PositionBudget, VacancyPlan, WorkforceScenario,
  ScenarioLineItem, OrgDesignScenario, OrgDesignNode,
  SpanOfControlSnapshot, WorkforceCostForecast, CostForecastLineItem,
  DepartmentBudgetActual, LocationWorkforcePlan, WorkforceMixPlan,
  CriticalRoleMapping, SuccessionCoveragePlan,
  SkillsDemandForecast, SkillsDemandLineItem,
  HiringRequisition, ReorgWorkflow, ReorgWorkflowTask
"""

from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import (
    HeadcountPlan,
    PositionBudget,
    VacancyPlan,
    WorkforceScenario,
    ScenarioLineItem,
    OrgDesignScenario,
    OrgDesignNode,
    SpanOfControlSnapshot,
    WorkforceCostForecast,
    CostForecastLineItem,
    DepartmentBudgetActual,
    LocationWorkforcePlan,
    WorkforceMixPlan,
    CriticalRoleMapping,
    SuccessionCoveragePlan,
    SkillsDemandForecast,
    SkillsDemandLineItem,
    HiringRequisition,
    ReorgWorkflow,
    ReorgWorkflowTask,
)


# ===========================================================================
# Serializers
# ===========================================================================

class HeadcountPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    headcount_gap = serializers.ReadOnlyField()
    budget_utilisation_pct = serializers.ReadOnlyField()

    class Meta:
        model = HeadcountPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class PositionBudgetSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    fte_variance = serializers.ReadOnlyField()
    budget_variance = serializers.ReadOnlyField()

    class Meta:
        model = PositionBudget
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class VacancyPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = VacancyPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class WorkforceScenarioSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = WorkforceScenario
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class ScenarioLineItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ScenarioLineItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class OrgDesignScenarioSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = OrgDesignScenario
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class OrgDesignNodeSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = OrgDesignNode
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class SpanOfControlSnapshotSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SpanOfControlSnapshot
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class WorkforceCostForecastSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = WorkforceCostForecast
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class CostForecastLineItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    variance = serializers.ReadOnlyField()

    class Meta:
        model = CostForecastLineItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class DepartmentBudgetActualSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    headcount_variance = serializers.ReadOnlyField()
    cost_variance = serializers.ReadOnlyField()

    class Meta:
        model = DepartmentBudgetActual
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class LocationWorkforcePlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    utilisation_pct = serializers.ReadOnlyField()

    class Meta:
        model = LocationWorkforcePlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class WorkforceMixPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    actual_fte_pct = serializers.ReadOnlyField()
    actual_contractor_pct = serializers.ReadOnlyField()

    class Meta:
        model = WorkforceMixPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class CriticalRoleMappingSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CriticalRoleMapping
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class SuccessionCoveragePlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SuccessionCoveragePlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'computed_at')


class SkillsDemandForecastSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SkillsDemandForecast
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class SkillsDemandLineItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SkillsDemandLineItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'gap_count')


class HiringRequisitionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = HiringRequisition
        fields = '__all__'
        read_only_fields = (
            'id', 'tenant', 'created_at', 'updated_at',
            'talentoss_synced_at',
        )


class ReorgWorkflowSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ReorgWorkflow
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class ReorgWorkflowTaskSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ReorgWorkflowTask
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


# ===========================================================================
# ViewSets
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. Headcount Plan
# ---------------------------------------------------------------------------

class HeadcountPlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Annual / quarterly headcount plans with approval workflow.

    Custom actions:
      POST /approve/         — approve the plan
      POST /lock/            — lock plan (no further changes)
      GET  /summary/         — headcount gap & budget utilisation summary
    """
    queryset = HeadcountPlan.objects.select_related('department', 'company').all()
    serializer_class = HeadcountPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['plan_year', 'period', 'department', 'company', 'status']
    search_fields = ['name']
    ordering_fields = ['plan_year', 'name', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_plans',
        'retrieve': 'workforce_planning.manage_plans',
        'create': 'workforce_planning.manage_plans',
        'update': 'workforce_planning.manage_plans',
        'partial_update': 'workforce_planning.manage_plans',
        'destroy': 'workforce_planning.manage_plans',
        'approve': 'workforce_planning.manage_plans',
        'lock': 'workforce_planning.manage_plans',
        'summary': 'workforce_planning.manage_plans',
    }

    def get_queryset(self):
        return HeadcountPlan.objects.select_related(
            'department', 'company'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a headcount plan."""
        plan = self.get_object()
        if plan.status == 'locked':
            return Response(
                {'error': 'Cannot approve a locked plan.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.status = 'approved'
        plan.approved_by = request.user
        plan.approved_at = timezone.now()
        plan.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response({'data': HeadcountPlanSerializer(plan).data})

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock an approved plan — no further edits allowed."""
        plan = self.get_object()
        if plan.status != 'approved':
            return Response(
                {'error': 'Only approved plans can be locked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.status = 'locked'
        plan.save(update_fields=['status'])
        return Response({'data': HeadcountPlanSerializer(plan).data})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Company-wide headcount gap summary for the current year.
        ?year=2025 to filter by year.
        """
        year = request.query_params.get('year', timezone.now().year)
        qs = self.get_queryset().filter(plan_year=year)
        agg = qs.aggregate(
            total_planned=Sum('planned_headcount'),
            total_current=Sum('current_headcount'),
            total_approved=Sum('approved_headcount'),
            total_budget=Sum('budget_amount'),
        )
        agg['total_gap'] = (agg['total_planned'] or 0) - (agg['total_current'] or 0)
        agg['plan_count'] = qs.count()
        return Response({'data': agg})


# ---------------------------------------------------------------------------
# 2. Position Budget
# ---------------------------------------------------------------------------

class PositionBudgetViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Position-level FTE budget and cost controls.

    Custom actions:
      GET  /fte_gaps/       — list positions with approved_fte > used_fte
      POST /freeze/         — set hiring freeze on a position budget
      POST /unfreeze/       — lift hiring freeze
    """
    queryset = PositionBudget.objects.select_related('position', 'plan').all()
    serializer_class = PositionBudgetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['position', 'plan', 'budget_year', 'is_critical_role', 'freeze_hiring']
    ordering_fields = ['budget_year', 'position', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_position_budgets',
        'retrieve': 'workforce_planning.manage_position_budgets',
        'create': 'workforce_planning.manage_position_budgets',
        'update': 'workforce_planning.manage_position_budgets',
        'partial_update': 'workforce_planning.manage_position_budgets',
        'destroy': 'workforce_planning.manage_position_budgets',
        'fte_gaps': 'workforce_planning.manage_position_budgets',
        'freeze': 'workforce_planning.manage_position_budgets',
        'unfreeze': 'workforce_planning.manage_position_budgets',
    }

    def get_queryset(self):
        return PositionBudget.objects.select_related(
            'position', 'plan'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def fte_gaps(self, request):
        """Return all positions where approved FTE > used FTE (open capacity)."""
        year = request.query_params.get('year', timezone.now().year)
        qs = self.get_queryset().filter(
            budget_year=year
        ).exclude(approved_fte=0)
        gaps = [
            {
                'id': str(pb.id),
                'position': str(pb.position),
                'approved_fte': float(pb.approved_fte),
                'used_fte': float(pb.used_fte),
                'fte_variance': pb.fte_variance,
                'freeze_hiring': pb.freeze_hiring,
            }
            for pb in qs
            if pb.fte_variance > 0
        ]
        return Response({'data': gaps})

    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        """Place a hiring freeze on this position budget."""
        pb = self.get_object()
        pb.freeze_hiring = True
        pb.save(update_fields=['freeze_hiring'])
        return Response({'data': PositionBudgetSerializer(pb).data})

    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        """Lift hiring freeze."""
        pb = self.get_object()
        pb.freeze_hiring = False
        pb.save(update_fields=['freeze_hiring'])
        return Response({'data': PositionBudgetSerializer(pb).data})


# ---------------------------------------------------------------------------
# 3. Vacancy Plan
# ---------------------------------------------------------------------------

class VacancyPlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Vacancy planning and backfill workflow management.

    Custom actions:
      POST /open/            — transition to 'open'
      POST /start_recruit/   — transition to 'in_recruitment', creates requisition
      POST /fill/            — mark as filled
      GET  /backfills/       — list all backfill vacancies
      GET  /pipeline/        — vacancy pipeline summary
    """
    queryset = VacancyPlan.objects.select_related(
        'position', 'department', 'backfill_for', 'requisition'
    ).all()
    serializer_class = VacancyPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['department', 'vacancy_type', 'status', 'plan']
    search_fields = ['position__title']
    ordering_fields = ['expected_vacancy_date', 'target_fill_date', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_vacancies',
        'retrieve': 'workforce_planning.manage_vacancies',
        'create': 'workforce_planning.manage_vacancies',
        'update': 'workforce_planning.manage_vacancies',
        'partial_update': 'workforce_planning.manage_vacancies',
        'destroy': 'workforce_planning.manage_vacancies',
        'open': 'workforce_planning.manage_vacancies',
        'start_recruit': 'workforce_planning.manage_vacancies',
        'fill': 'workforce_planning.manage_vacancies',
        'backfills': 'workforce_planning.manage_vacancies',
        'pipeline': 'workforce_planning.manage_vacancies',
    }

    def get_queryset(self):
        return VacancyPlan.objects.select_related(
            'position', 'department', 'backfill_for', 'requisition'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def open(self, request, pk=None):
        """Transition vacancy to open status."""
        vacancy = self.get_object()
        vacancy.status = 'open'
        vacancy.save(update_fields=['status'])
        return Response({'data': VacancyPlanSerializer(vacancy).data})

    @action(detail=True, methods=['post'])
    def start_recruit(self, request, pk=None):
        """Transition to in_recruitment — optionally links a requisition."""
        vacancy = self.get_object()
        vacancy.status = 'in_recruitment'
        vacancy.save(update_fields=['status'])
        return Response({'data': VacancyPlanSerializer(vacancy).data})

    @action(detail=True, methods=['post'])
    def fill(self, request, pk=None):
        """Mark vacancy as filled."""
        vacancy = self.get_object()
        from datetime import date
        vacancy.status = 'filled'
        vacancy.actual_fill_date = date.today()
        vacancy.save(update_fields=['status', 'actual_fill_date'])
        return Response({'data': VacancyPlanSerializer(vacancy).data})

    @action(detail=False, methods=['get'])
    def backfills(self, request):
        """All active backfill vacancies."""
        qs = self.get_queryset().filter(
            vacancy_type='backfill'
        ).exclude(status__in=['filled', 'cancelled'])
        return Response({'data': VacancyPlanSerializer(qs, many=True).data})

    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """Vacancy pipeline summary by status."""
        qs = self.get_queryset()
        summary = qs.values('status').annotate(count=Count('id')).order_by('status')
        return Response({'data': list(summary)})


# ---------------------------------------------------------------------------
# 4. Workforce Scenario
# ---------------------------------------------------------------------------

class WorkforceScenarioViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Workforce scenario planning (growth, freeze, restructure, downsizing).

    Custom actions:
      POST /approve/         — approve scenario
      POST /implement/       — mark as implemented
      POST /discard/         — discard scenario
      GET  /compare/         — compare two scenarios (?a=<id>&b=<id>)
      POST /compute_totals/  — recompute projected_headcount / cost from line items
    """
    queryset = WorkforceScenario.objects.all()
    serializer_class = WorkforceScenarioSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scenario_type', 'status', 'base_year']
    search_fields = ['name']
    ordering_fields = ['name', 'base_year', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_scenarios',
        'retrieve': 'workforce_planning.manage_scenarios',
        'create': 'workforce_planning.manage_scenarios',
        'update': 'workforce_planning.manage_scenarios',
        'partial_update': 'workforce_planning.manage_scenarios',
        'destroy': 'workforce_planning.manage_scenarios',
        'approve': 'workforce_planning.manage_scenarios',
        'implement': 'workforce_planning.manage_scenarios',
        'discard': 'workforce_planning.manage_scenarios',
        'compare': 'workforce_planning.manage_scenarios',
        'compute_totals': 'workforce_planning.manage_scenarios',
    }

    def get_queryset(self):
        return WorkforceScenario.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        scenario = self.get_object()
        scenario.status = 'approved'
        scenario.approved_by = request.user
        scenario.approved_at = timezone.now()
        scenario.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response({'data': WorkforceScenarioSerializer(scenario).data})

    @action(detail=True, methods=['post'])
    def implement(self, request, pk=None):
        scenario = self.get_object()
        if scenario.status != 'approved':
            return Response(
                {'error': 'Only approved scenarios can be implemented.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scenario.status = 'implemented'
        scenario.save(update_fields=['status'])
        return Response({'data': WorkforceScenarioSerializer(scenario).data})

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        scenario = self.get_object()
        scenario.status = 'discarded'
        scenario.save(update_fields=['status'])
        return Response({'data': WorkforceScenarioSerializer(scenario).data})

    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Side-by-side comparison of two scenarios by their UUIDs."""
        a_id = request.query_params.get('a')
        b_id = request.query_params.get('b')
        if not a_id or not b_id:
            return Response(
                {'error': 'Provide both ?a=<uuid>&b=<uuid> params.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset()
        try:
            a = qs.get(pk=a_id)
            b = qs.get(pk=b_id)
        except WorkforceScenario.DoesNotExist:
            return Response({'error': 'Scenario not found.'}, status=status.HTTP_404_NOT_FOUND)

        def _delta(val_a, val_b):
            if val_a is None or val_b is None:
                return None
            return float(val_b) - float(val_a)

        comparison = {
            'scenario_a': WorkforceScenarioSerializer(a).data,
            'scenario_b': WorkforceScenarioSerializer(b).data,
            'deltas': {
                'projected_headcount': _delta(a.projected_headcount, b.projected_headcount),
                'projected_cost': _delta(a.projected_cost, b.projected_cost),
                'headcount_delta': _delta(a.headcount_delta, b.headcount_delta),
                'cost_delta': _delta(a.cost_delta, b.cost_delta),
            },
        }
        return Response({'data': comparison})

    @action(detail=True, methods=['post'])
    def compute_totals(self, request, pk=None):
        """Recompute projected_headcount and projected_cost from line items."""
        scenario = self.get_object()
        agg = scenario.line_items.aggregate(
            hc_sum=Sum('headcount_change'),
            cost_sum=Sum('cost_impact'),
        )
        scenario.headcount_delta = agg['hc_sum'] or 0
        scenario.projected_headcount = (
            (request.data.get('base_headcount') or 0) + scenario.headcount_delta
        )
        scenario.cost_delta = agg['cost_sum'] or 0
        scenario.save(update_fields=['headcount_delta', 'projected_headcount', 'cost_delta'])
        return Response({'data': WorkforceScenarioSerializer(scenario).data})


# ---------------------------------------------------------------------------
# 5. Scenario Line Item
# ---------------------------------------------------------------------------

class ScenarioLineItemViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Year-by-year line items for workforce scenarios."""
    queryset = ScenarioLineItem.objects.select_related('scenario', 'department', 'position').all()
    serializer_class = ScenarioLineItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['scenario', 'year', 'quarter', 'department', 'change_type']
    ordering_fields = ['year', 'quarter']
    required_permissions = {
        'list': 'workforce_planning.manage_scenarios',
        'retrieve': 'workforce_planning.manage_scenarios',
        'create': 'workforce_planning.manage_scenarios',
        'update': 'workforce_planning.manage_scenarios',
        'partial_update': 'workforce_planning.manage_scenarios',
        'destroy': 'workforce_planning.manage_scenarios',
    }

    def get_queryset(self):
        return ScenarioLineItem.objects.select_related(
            'scenario', 'department', 'position'
        ).filter(tenant_id=self.request.tenant_id)


# ---------------------------------------------------------------------------
# 6. Org Design Scenario
# ---------------------------------------------------------------------------

class OrgDesignScenarioViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Future org-chart modeling scenarios.

    Custom actions:
      POST /approve/          — approve the scenario
      POST /discard/          — discard the scenario
      GET  /impact_summary/   — compute headcount + cost impact from nodes
    """
    queryset = OrgDesignScenario.objects.all()
    serializer_class = OrgDesignScenarioSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'status']
    required_permissions = {
        'list': 'workforce_planning.manage_org_scenarios',
        'retrieve': 'workforce_planning.manage_org_scenarios',
        'create': 'workforce_planning.manage_org_scenarios',
        'update': 'workforce_planning.manage_org_scenarios',
        'partial_update': 'workforce_planning.manage_org_scenarios',
        'destroy': 'workforce_planning.manage_org_scenarios',
        'approve': 'workforce_planning.manage_org_scenarios',
        'discard': 'workforce_planning.manage_org_scenarios',
        'impact_summary': 'workforce_planning.manage_org_scenarios',
    }

    def get_queryset(self):
        return OrgDesignScenario.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        scenario = self.get_object()
        scenario.status = 'approved'
        scenario.approved_by = request.user
        scenario.save(update_fields=['status', 'approved_by'])
        return Response({'data': OrgDesignScenarioSerializer(scenario).data})

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        scenario = self.get_object()
        scenario.status = 'discarded'
        scenario.save(update_fields=['status'])
        return Response({'data': OrgDesignScenarioSerializer(scenario).data})

    @action(detail=True, methods=['get'])
    def impact_summary(self, request, pk=None):
        """Aggregate headcount and cost impact from all nodes in this scenario."""
        scenario = self.get_object()
        agg = scenario.nodes.aggregate(
            total_hc_impact=Sum('headcount_impact'),
            total_cost_impact=Sum('cost_impact'),
        )
        # Update cached fields
        scenario.headcount_impact = agg['total_hc_impact'] or 0
        scenario.cost_impact = agg['total_cost_impact'] or 0
        scenario.save(update_fields=['headcount_impact', 'cost_impact'])
        return Response({
            'data': {
                'headcount_impact': scenario.headcount_impact,
                'cost_impact': str(scenario.cost_impact),
                'node_count': scenario.nodes.count(),
            }
        })


# ---------------------------------------------------------------------------
# 7. Org Design Node
# ---------------------------------------------------------------------------

class OrgDesignNodeViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Individual node changes within an org design scenario."""
    queryset = OrgDesignNode.objects.select_related(
        'scenario', 'ref_department', 'ref_position'
    ).all()
    serializer_class = OrgDesignNodeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['scenario', 'node_type', 'change_action']
    ordering_fields = ['sequence']
    required_permissions = {
        'list': 'workforce_planning.manage_org_scenarios',
        'retrieve': 'workforce_planning.manage_org_scenarios',
        'create': 'workforce_planning.manage_org_scenarios',
        'update': 'workforce_planning.manage_org_scenarios',
        'partial_update': 'workforce_planning.manage_org_scenarios',
        'destroy': 'workforce_planning.manage_org_scenarios',
    }

    def get_queryset(self):
        return OrgDesignNode.objects.select_related(
            'scenario', 'ref_department', 'ref_position'
        ).filter(tenant_id=self.request.tenant_id)


# ---------------------------------------------------------------------------
# 8. Span of Control Snapshot
# ---------------------------------------------------------------------------

class SpanOfControlSnapshotViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Span-of-control and management-layer analysis snapshots.

    Custom actions:
      POST /compute/      — compute and save a new snapshot for today
      GET  /analysis/     — management layer distribution and anomalies
    """
    queryset = SpanOfControlSnapshot.objects.select_related('company', 'department', 'manager').all()
    serializer_class = SpanOfControlSnapshotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['snapshot_date', 'company', 'department', 'management_layer']
    ordering_fields = ['snapshot_date', 'management_layer', 'direct_report_count']
    required_permissions = {
        'list': 'workforce_planning.manage_span_analysis',
        'retrieve': 'workforce_planning.manage_span_analysis',
        'create': 'workforce_planning.manage_span_analysis',
        'update': 'workforce_planning.manage_span_analysis',
        'partial_update': 'workforce_planning.manage_span_analysis',
        'destroy': 'workforce_planning.manage_span_analysis',
        'compute': 'workforce_planning.manage_span_analysis',
        'analysis': 'workforce_planning.manage_span_analysis',
    }

    def get_queryset(self):
        return SpanOfControlSnapshot.objects.select_related(
            'company', 'department', 'manager'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['post'])
    def compute(self, request):
        """
        Compute span-of-control from live employee data and persist snapshot.
        Iterates all active managers and counts their direct reports.
        """
        from datetime import date
        from core_hr.models import Employee

        today = date.today()
        tenant_id = request.tenant_id

        managers = Employee.objects.filter(
            tenant_id=tenant_id,
            status='active',
        ).exclude(direct_reports__isnull=True)

        created_count = 0
        for manager in managers:
            direct_count = manager.direct_reports.filter(status='active').count()
            if direct_count == 0:
                continue

            SpanOfControlSnapshot.objects.update_or_create(
                tenant_id=tenant_id,
                snapshot_date=today,
                manager=manager,
                defaults={
                    'direct_report_count': direct_count,
                    'total_report_count': direct_count,  # simplified; deep count optional
                    'management_layer': 1,  # simplified; full tree traversal optional
                    'company': manager.company,
                    'department': manager.department,
                },
            )
            created_count += 1

        return Response({
            'data': {
                'snapshot_date': today.isoformat(),
                'managers_processed': created_count,
            }
        })

    @action(detail=False, methods=['get'])
    def analysis(self, request):
        """Management layer distribution and span anomalies."""
        qs = self.get_queryset()
        date_filter = request.query_params.get('date')
        if date_filter:
            qs = qs.filter(snapshot_date=date_filter)
        else:
            # latest snapshot date
            latest = qs.order_by('-snapshot_date').values_list('snapshot_date', flat=True).first()
            if latest:
                qs = qs.filter(snapshot_date=latest)

        layer_dist = qs.values('management_layer').annotate(
            manager_count=Count('id'),
            avg_span=Avg('direct_report_count'),
        ).order_by('management_layer')

        anomalies = {
            'over_span': SpanOfControlSnapshotSerializer(
                qs.filter(direct_report_count__gt=10), many=True
            ).data,
            'under_span': SpanOfControlSnapshotSerializer(
                qs.filter(direct_report_count__lt=2), many=True
            ).data,
        }

        return Response({
            'data': {
                'layer_distribution': list(layer_dist),
                'anomalies': anomalies,
            }
        })


# ---------------------------------------------------------------------------
# 9. Workforce Cost Forecast
# ---------------------------------------------------------------------------

class WorkforceCostForecastViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Workforce cost forecasting (salary, benefits, recruitment, contractor).

    Custom actions:
      POST /compute/          — run cost computation and cache totals
      POST /approve/          — approve forecast
      GET  /trend/            — multi-year trend from line items
    """
    queryset = WorkforceCostForecast.objects.select_related('company').all()
    serializer_class = WorkforceCostForecastSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['forecast_year', 'company', 'status']
    search_fields = ['name']
    ordering_fields = ['forecast_year', 'name', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_cost_forecasts',
        'retrieve': 'workforce_planning.manage_cost_forecasts',
        'create': 'workforce_planning.manage_cost_forecasts',
        'update': 'workforce_planning.manage_cost_forecasts',
        'partial_update': 'workforce_planning.manage_cost_forecasts',
        'destroy': 'workforce_planning.manage_cost_forecasts',
        'compute': 'workforce_planning.manage_cost_forecasts',
        'approve': 'workforce_planning.manage_cost_forecasts',
        'trend': 'workforce_planning.manage_cost_forecasts',
    }

    def get_queryset(self):
        return WorkforceCostForecast.objects.select_related(
            'company'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def compute(self, request, pk=None):
        """Recompute and cache total workforce costs from inputs."""
        forecast = self.get_object()
        forecast.compute_totals()
        forecast.save(update_fields=[
            'total_salary_cost', 'total_benefits_cost',
            'total_recruitment_cost', 'total_workforce_cost',
        ])
        return Response({'data': WorkforceCostForecastSerializer(forecast).data})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        forecast = self.get_object()
        forecast.status = 'approved'
        forecast.approved_by = request.user
        forecast.save(update_fields=['status', 'approved_by'])
        return Response({'data': WorkforceCostForecastSerializer(forecast).data})

    @action(detail=True, methods=['get'])
    def trend(self, request, pk=None):
        """Multi-year cost trend from line items."""
        forecast = self.get_object()
        trend = forecast.line_items.values('year', 'cost_category').annotate(
            total_budgeted=Sum('budgeted_amount'),
            total_actual=Sum('actual_amount'),
        ).order_by('year', 'cost_category')
        return Response({'data': list(trend)})


# ---------------------------------------------------------------------------
# 10. Cost Forecast Line Item
# ---------------------------------------------------------------------------

class CostForecastLineItemViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Year/department/category line items for cost forecasts."""
    queryset = CostForecastLineItem.objects.select_related('forecast', 'department').all()
    serializer_class = CostForecastLineItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['forecast', 'year', 'department', 'cost_category']
    ordering_fields = ['year', 'cost_category']
    required_permissions = {
        'list': 'workforce_planning.manage_cost_forecasts',
        'retrieve': 'workforce_planning.manage_cost_forecasts',
        'create': 'workforce_planning.manage_cost_forecasts',
        'update': 'workforce_planning.manage_cost_forecasts',
        'partial_update': 'workforce_planning.manage_cost_forecasts',
        'destroy': 'workforce_planning.manage_cost_forecasts',
    }

    def get_queryset(self):
        return CostForecastLineItem.objects.select_related(
            'forecast', 'department'
        ).filter(tenant_id=self.request.tenant_id)


# ---------------------------------------------------------------------------
# 11. Department Budget vs Actual
# ---------------------------------------------------------------------------

class DepartmentBudgetActualViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Department headcount budget vs actual tracking.

    Custom actions:
      GET  /variance_report/  — departments with highest variance
    """
    queryset = DepartmentBudgetActual.objects.select_related('department', 'plan').all()
    serializer_class = DepartmentBudgetActualSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['department', 'period_type', 'period_year', 'period_number', 'plan']
    ordering_fields = ['period_year', 'period_number', 'department']
    required_permissions = {
        'list': 'workforce_planning.manage_budget_actuals',
        'retrieve': 'workforce_planning.manage_budget_actuals',
        'create': 'workforce_planning.manage_budget_actuals',
        'update': 'workforce_planning.manage_budget_actuals',
        'partial_update': 'workforce_planning.manage_budget_actuals',
        'destroy': 'workforce_planning.manage_budget_actuals',
        'variance_report': 'workforce_planning.manage_budget_actuals',
    }

    def get_queryset(self):
        return DepartmentBudgetActual.objects.select_related(
            'department', 'plan'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def variance_report(self, request):
        """
        Returns departments sorted by absolute headcount variance.
        ?year=2025&period_type=monthly
        """
        year = request.query_params.get('year', timezone.now().year)
        period_type = request.query_params.get('period_type', 'monthly')
        qs = self.get_queryset().filter(
            period_year=year, period_type=period_type
        ).select_related('department')
        items = DepartmentBudgetActualSerializer(qs, many=True).data
        # Sort by abs(headcount_variance) descending
        items_sorted = sorted(
            items, key=lambda x: abs(x.get('headcount_variance') or 0), reverse=True
        )
        return Response({'data': items_sorted})


# ---------------------------------------------------------------------------
# 12. Location Workforce Plan
# ---------------------------------------------------------------------------

class LocationWorkforcePlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Site and location-level workforce planning.

    Custom actions:
      GET  /by_country/    — aggregate headcount by country
      GET  /capacity_gaps/ — locations where onsite_count > office_capacity
    """
    queryset = LocationWorkforcePlan.objects.select_related('plan').all()
    serializer_class = LocationWorkforcePlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['country', 'plan_year', 'status', 'plan']
    search_fields = ['location_name', 'city']
    ordering_fields = ['location_name', 'plan_year', 'planned_headcount']
    required_permissions = {
        'list': 'workforce_planning.manage_location_plans',
        'retrieve': 'workforce_planning.manage_location_plans',
        'create': 'workforce_planning.manage_location_plans',
        'update': 'workforce_planning.manage_location_plans',
        'partial_update': 'workforce_planning.manage_location_plans',
        'destroy': 'workforce_planning.manage_location_plans',
        'by_country': 'workforce_planning.manage_location_plans',
        'capacity_gaps': 'workforce_planning.manage_location_plans',
    }

    def get_queryset(self):
        return LocationWorkforcePlan.objects.select_related(
            'plan'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=False, methods=['get'])
    def by_country(self, request):
        """Aggregate planned and current headcount by country."""
        year = request.query_params.get('year', timezone.now().year)
        agg = self.get_queryset().filter(plan_year=year).values('country').annotate(
            total_planned=Sum('planned_headcount'),
            total_current=Sum('current_headcount'),
            total_fte=Sum('fte_count'),
            total_contractors=Sum('contractor_count'),
            location_count=Count('id'),
        ).order_by('country')
        return Response({'data': list(agg)})

    @action(detail=False, methods=['get'])
    def capacity_gaps(self, request):
        """Locations where onsite count exceeds office capacity."""
        qs = self.get_queryset().exclude(office_capacity__isnull=True).filter(
            onsite_count__gt=0
        )
        gaps = [
            LocationWorkforcePlanSerializer(loc).data
            for loc in qs
            if loc.office_capacity and loc.onsite_count > loc.office_capacity
        ]
        return Response({'data': gaps})


# ---------------------------------------------------------------------------
# 13. Workforce Mix Plan
# ---------------------------------------------------------------------------

class WorkforceMixPlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Contractor vs FTE workforce mix planning.

    Custom actions:
      GET  /mix_dashboard/    — company-wide mix actuals vs targets
    """
    queryset = WorkforceMixPlan.objects.select_related('department', 'plan').all()
    serializer_class = WorkforceMixPlanSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['department', 'plan_year', 'plan']
    ordering_fields = ['plan_year', 'department']
    required_permissions = {
        'list': 'workforce_planning.manage_mix_plans',
        'retrieve': 'workforce_planning.manage_mix_plans',
        'create': 'workforce_planning.manage_mix_plans',
        'update': 'workforce_planning.manage_mix_plans',
        'partial_update': 'workforce_planning.manage_mix_plans',
        'destroy': 'workforce_planning.manage_mix_plans',
        'mix_dashboard': 'workforce_planning.manage_mix_plans',
    }

    def get_queryset(self):
        return WorkforceMixPlan.objects.select_related(
            'department', 'plan'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=False, methods=['get'])
    def mix_dashboard(self, request):
        """Company-wide mix dashboard: targets vs actuals by department."""
        year = request.query_params.get('year', timezone.now().year)
        qs = self.get_queryset().filter(plan_year=year)
        data = WorkforceMixPlanSerializer(qs, many=True).data
        totals = qs.aggregate(
            total_fte=Sum('actual_fte_count'),
            total_contractors=Sum('actual_contractor_count'),
            total_interns=Sum('actual_intern_count'),
            total_workforce=Sum('actual_total_count'),
        )
        return Response({'data': {'by_department': data, 'totals': totals}})


# ---------------------------------------------------------------------------
# 14. Critical Role Mapping
# ---------------------------------------------------------------------------

class CriticalRoleMappingViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Critical role mapping and succession coverage status.

    Custom actions:
      GET  /coverage_gap/       — critical roles with no successor (gap)
      POST /update_coverage/    — refresh coverage_status based on successor_count
    """
    queryset = CriticalRoleMapping.objects.select_related(
        'position', 'critical_role_ref', 'plan'
    ).all()
    serializer_class = CriticalRoleMappingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['impact_level', 'coverage_status', 'is_critical_role', 'plan']
    search_fields = ['position__title']
    ordering_fields = ['impact_level', 'coverage_status', 'successor_count']
    required_permissions = {
        'list': 'workforce_planning.manage_critical_roles',
        'retrieve': 'workforce_planning.manage_critical_roles',
        'create': 'workforce_planning.manage_critical_roles',
        'update': 'workforce_planning.manage_critical_roles',
        'partial_update': 'workforce_planning.manage_critical_roles',
        'destroy': 'workforce_planning.manage_critical_roles',
        'coverage_gap': 'workforce_planning.manage_critical_roles',
        'update_coverage': 'workforce_planning.manage_critical_roles',
    }

    def get_queryset(self):
        return CriticalRoleMapping.objects.select_related(
            'position', 'critical_role_ref', 'plan'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=False, methods=['get'])
    def coverage_gap(self, request):
        """All critical roles with coverage_status == 'gap'."""
        qs = self.get_queryset().filter(coverage_status='gap')
        return Response({'data': CriticalRoleMappingSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'])
    def update_coverage(self, request, pk=None):
        """
        Update coverage_status based on successor_count provided in request body.
        Body: { successor_count: int }
        """
        mapping = self.get_object()
        count = request.data.get('successor_count', mapping.successor_count)
        mapping.successor_count = int(count)
        if mapping.successor_count == 0:
            mapping.coverage_status = 'gap'
        elif mapping.successor_count == 1:
            mapping.coverage_status = 'at_risk'
        else:
            mapping.coverage_status = 'covered'
        mapping.save(update_fields=['successor_count', 'coverage_status'])
        return Response({'data': CriticalRoleMappingSerializer(mapping).data})


# ---------------------------------------------------------------------------
# 15. Succession Coverage Plan
# ---------------------------------------------------------------------------

class SuccessionCoveragePlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Company-level succession coverage summary.

    Custom actions:
      POST /recompute/    — recompute coverage_pct and readiness_score
    """
    queryset = SuccessionCoveragePlan.objects.select_related('company', 'plan').all()
    serializer_class = SuccessionCoveragePlanSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['plan_year', 'company', 'plan']
    ordering_fields = ['plan_year', 'coverage_pct']
    required_permissions = {
        'list': 'workforce_planning.manage_succession_coverage',
        'retrieve': 'workforce_planning.manage_succession_coverage',
        'create': 'workforce_planning.manage_succession_coverage',
        'update': 'workforce_planning.manage_succession_coverage',
        'partial_update': 'workforce_planning.manage_succession_coverage',
        'destroy': 'workforce_planning.manage_succession_coverage',
        'recompute': 'workforce_planning.manage_succession_coverage',
    }

    def get_queryset(self):
        return SuccessionCoveragePlan.objects.select_related(
            'company', 'plan'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def recompute(self, request, pk=None):
        """Recompute coverage_pct and readiness_score from raw counts."""
        plan = self.get_object()
        plan.recompute()
        plan.save(update_fields=['coverage_pct', 'readiness_score'])
        return Response({'data': SuccessionCoveragePlanSerializer(plan).data})


# ---------------------------------------------------------------------------
# 16. Skills Demand Forecast
# ---------------------------------------------------------------------------

class SkillsDemandForecastViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Skills demand forecasting by function.

    Custom actions:
      GET  /critical_gaps/  — skills with demand_trend==critical_shortage or large gap
    """
    queryset = SkillsDemandForecast.objects.select_related('company', 'linked_scenario').all()
    serializer_class = SkillsDemandForecastSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['forecast_year', 'company', 'status']
    search_fields = ['name']
    ordering_fields = ['forecast_year', 'name']
    required_permissions = {
        'list': 'workforce_planning.manage_skills_forecasts',
        'retrieve': 'workforce_planning.manage_skills_forecasts',
        'create': 'workforce_planning.manage_skills_forecasts',
        'update': 'workforce_planning.manage_skills_forecasts',
        'partial_update': 'workforce_planning.manage_skills_forecasts',
        'destroy': 'workforce_planning.manage_skills_forecasts',
        'critical_gaps': 'workforce_planning.manage_skills_forecasts',
    }

    def get_queryset(self):
        return SkillsDemandForecast.objects.select_related(
            'company', 'linked_scenario'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['get'])
    def critical_gaps(self, request, pk=None):
        """Skills with critical_shortage demand trend or gap_count > 5."""
        forecast = self.get_object()
        critical = forecast.line_items.filter(
            Q(demand_trend='critical_shortage') | Q(gap_count__gt=5)
        ).order_by('-gap_count')
        return Response({
            'data': SkillsDemandLineItemSerializer(critical, many=True).data
        })


# ---------------------------------------------------------------------------
# 17. Skills Demand Line Item
# ---------------------------------------------------------------------------

class SkillsDemandLineItemViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Individual skills demand line items for forecasts."""
    queryset = SkillsDemandLineItem.objects.select_related('forecast', 'department').all()
    serializer_class = SkillsDemandLineItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['forecast', 'year', 'department', 'demand_trend', 'gap_strategy']
    search_fields = ['skill_name', 'skill_category']
    ordering_fields = ['year', 'skill_name', 'gap_count']
    required_permissions = {
        'list': 'workforce_planning.manage_skills_forecasts',
        'retrieve': 'workforce_planning.manage_skills_forecasts',
        'create': 'workforce_planning.manage_skills_forecasts',
        'update': 'workforce_planning.manage_skills_forecasts',
        'partial_update': 'workforce_planning.manage_skills_forecasts',
        'destroy': 'workforce_planning.manage_skills_forecasts',
    }

    def get_queryset(self):
        return SkillsDemandLineItem.objects.select_related(
            'forecast', 'department'
        ).filter(tenant_id=self.request.tenant_id)


# ---------------------------------------------------------------------------
# 18. Hiring Requisition  (with TalentOS handoff)
# ---------------------------------------------------------------------------

class HiringRequisitionViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Hiring requisitions with TalentOS / ATS handoff.

    Custom actions:
      POST /approve/          — approve requisition
      POST /on_hold/          — put on hold
      POST /cancel/           — cancel requisition
      POST /fill/             — mark as filled
      POST /send_to_talentoss/ — handoff to TalentOS ATS
      GET  /open_reqs/        — all approved/in_progress requisitions
      GET  /talentoss_pending/ — reqs not yet sent to TalentOS
    """
    queryset = HiringRequisition.objects.select_related(
        'department', 'position', 'plan', 'hiring_manager'
    ).all()
    serializer_class = HiringRequisitionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'department', 'status', 'priority', 'employment_type',
        'reason', 'talentoss_sync_status',
    ]
    search_fields = ['title', 'requisition_number']
    ordering_fields = ['created_at', 'target_start_date', 'priority']
    required_permissions = {
        'list': 'workforce_planning.manage_requisitions',
        'retrieve': 'workforce_planning.manage_requisitions',
        'create': 'workforce_planning.manage_requisitions',
        'update': 'workforce_planning.manage_requisitions',
        'partial_update': 'workforce_planning.manage_requisitions',
        'destroy': 'workforce_planning.manage_requisitions',
        'approve': 'workforce_planning.manage_requisitions',
        'on_hold': 'workforce_planning.manage_requisitions',
        'cancel': 'workforce_planning.manage_requisitions',
        'fill': 'workforce_planning.manage_requisitions',
        'send_to_talentoss': 'workforce_planning.manage_requisitions',
        'open_reqs': 'workforce_planning.manage_requisitions',
        'talentoss_pending': 'workforce_planning.manage_requisitions',
    }

    def get_queryset(self):
        return HiringRequisition.objects.select_related(
            'department', 'position', 'plan', 'hiring_manager'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        req.status = 'approved'
        req.approved_by = request.user
        req.approved_at = timezone.now()
        req.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response({'data': HiringRequisitionSerializer(req).data})

    @action(detail=True, methods=['post'])
    def on_hold(self, request, pk=None):
        req = self.get_object()
        req.status = 'on_hold'
        req.save(update_fields=['status'])
        return Response({'data': HiringRequisitionSerializer(req).data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        req = self.get_object()
        req.status = 'cancelled'
        req.save(update_fields=['status'])
        return Response({'data': HiringRequisitionSerializer(req).data})

    @action(detail=True, methods=['post'])
    def fill(self, request, pk=None):
        from datetime import date
        req = self.get_object()
        req.status = 'filled'
        req.filled_at = date.today()
        req.save(update_fields=['status', 'filled_at'])
        return Response({'data': HiringRequisitionSerializer(req).data})

    @action(detail=True, methods=['post'])
    def send_to_talentoss(self, request, pk=None):
        """
        Handoff this approved requisition to TalentOS ATS.
        Calls the ATS integration endpoint and records the resulting job_id.
        """
        req = self.get_object()
        if req.status not in ('approved', 'in_progress'):
            return Response(
                {'error': 'Only approved or in-progress requisitions can be sent to TalentOS.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.conf import settings as django_settings
        import requests as http_requests

        ats_url = getattr(django_settings, 'ATS_BASE_URL', '')
        if not ats_url:
            return Response(
                {'error': 'ATS_BASE_URL not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload = {
            'requisition_id': str(req.id),
            'title': req.title,
            'department': str(req.department),
            'employment_type': req.employment_type,
            'salary_range_min': str(req.salary_range_min or ''),
            'salary_range_max': str(req.salary_range_max or ''),
            'currency': req.currency,
            'required_skills': req.required_skills,
            'job_description': req.job_description,
            'priority': req.priority,
            'target_start_date': req.target_start_date.isoformat() if req.target_start_date else None,
        }

        try:
            resp = http_requests.post(
                f"{ats_url.rstrip('/')}/api/v1/jobs/from-requisition/",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            job_id = resp.json().get('id', '')
        except Exception as exc:
            req.talentoss_sync_status = 'error'
            req.save(update_fields=['talentoss_sync_status'])
            return Response(
                {'error': f'TalentOS handoff failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        req.talentoss_job_id = str(job_id)
        req.talentoss_sync_status = 'sent'
        req.talentoss_synced_at = timezone.now()
        req.status = 'in_progress'
        req.save(update_fields=[
            'talentoss_job_id', 'talentoss_sync_status',
            'talentoss_synced_at', 'status',
        ])
        return Response({'data': HiringRequisitionSerializer(req).data})

    @action(detail=False, methods=['get'])
    def open_reqs(self, request):
        """All open (approved / in_progress) requisitions."""
        qs = self.get_queryset().filter(status__in=['approved', 'in_progress'])
        return Response({'data': HiringRequisitionSerializer(qs, many=True).data})

    @action(detail=False, methods=['get'])
    def talentoss_pending(self, request):
        """Approved requisitions not yet sent to TalentOS."""
        qs = self.get_queryset().filter(
            status='approved',
            talentoss_sync_status='not_sent',
        )
        return Response({'data': HiringRequisitionSerializer(qs, many=True).data})


# ---------------------------------------------------------------------------
# 19. Reorg Workflow
# ---------------------------------------------------------------------------

class ReorgWorkflowViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Change-management workflows for org restructures.

    Custom actions:
      POST /advance/          — advance to next status in workflow
      POST /complete/         — mark workflow as completed
      POST /cancel/           — cancel workflow
      GET  /task_summary/     — pending / completed / blocked task counts
    """
    queryset = ReorgWorkflow.objects.select_related(
        'org_scenario', 'workforce_scenario', 'executive_sponsor', 'hr_lead'
    ).all()
    serializer_class = ReorgWorkflowSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['reorg_type', 'status']
    search_fields = ['name']
    ordering_fields = ['name', 'effective_date', 'created_at']
    required_permissions = {
        'list': 'workforce_planning.manage_reorg_workflows',
        'retrieve': 'workforce_planning.manage_reorg_workflows',
        'create': 'workforce_planning.manage_reorg_workflows',
        'update': 'workforce_planning.manage_reorg_workflows',
        'partial_update': 'workforce_planning.manage_reorg_workflows',
        'destroy': 'workforce_planning.manage_reorg_workflows',
        'advance': 'workforce_planning.manage_reorg_workflows',
        'complete': 'workforce_planning.manage_reorg_workflows',
        'cancel': 'workforce_planning.manage_reorg_workflows',
        'task_summary': 'workforce_planning.manage_reorg_workflows',
    }

    # Status progression order
    _STATUS_ORDER = [
        'planning', 'impact_assessment', 'executive_review',
        'approved', 'communication', 'implementation', 'completed',
    ]

    def get_queryset(self):
        return ReorgWorkflow.objects.select_related(
            'org_scenario', 'workforce_scenario', 'executive_sponsor', 'hr_lead'
        ).filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        """Advance to the next status in the workflow progression."""
        workflow = self.get_object()
        try:
            current_idx = self._STATUS_ORDER.index(workflow.status)
        except ValueError:
            return Response(
                {'error': f'Cannot advance from status: {workflow.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if current_idx >= len(self._STATUS_ORDER) - 1:
            return Response({'error': 'Workflow is already at final status.'}, status=400)
        workflow.status = self._STATUS_ORDER[current_idx + 1]
        workflow.save(update_fields=['status'])
        return Response({'data': ReorgWorkflowSerializer(workflow).data})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from datetime import date
        workflow = self.get_object()
        workflow.status = 'completed'
        workflow.completion_date = date.today()
        workflow.save(update_fields=['status', 'completion_date'])
        return Response({'data': ReorgWorkflowSerializer(workflow).data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        workflow = self.get_object()
        workflow.status = 'cancelled'
        workflow.save(update_fields=['status'])
        return Response({'data': ReorgWorkflowSerializer(workflow).data})

    @action(detail=True, methods=['get'])
    def task_summary(self, request, pk=None):
        """Count of tasks by status for this reorg workflow."""
        workflow = self.get_object()
        summary = workflow.tasks.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        mandatory_pending = workflow.tasks.filter(
            is_mandatory=True,
            status__in=['pending', 'blocked'],
        ).count()
        return Response({
            'data': {
                'by_status': list(summary),
                'mandatory_pending': mandatory_pending,
                'total': workflow.tasks.count(),
            }
        })


# ---------------------------------------------------------------------------
# 20. Reorg Workflow Task
# ---------------------------------------------------------------------------

class ReorgWorkflowTaskViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Individual tasks within reorg change-management workflows.

    Custom actions:
      POST /complete/   — mark task as completed
      POST /block/      — flag as blocked
    """
    queryset = ReorgWorkflowTask.objects.select_related('workflow', 'assigned_to').all()
    serializer_class = ReorgWorkflowTaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['workflow', 'task_type', 'status', 'is_mandatory', 'assigned_to']
    search_fields = ['title']
    ordering_fields = ['sequence', 'due_date']
    required_permissions = {
        'list': 'workforce_planning.manage_reorg_workflows',
        'retrieve': 'workforce_planning.manage_reorg_workflows',
        'create': 'workforce_planning.manage_reorg_workflows',
        'update': 'workforce_planning.manage_reorg_workflows',
        'partial_update': 'workforce_planning.manage_reorg_workflows',
        'destroy': 'workforce_planning.manage_reorg_workflows',
        'complete': 'workforce_planning.manage_reorg_workflows',
        'block': 'workforce_planning.manage_reorg_workflows',
    }

    def get_queryset(self):
        return ReorgWorkflowTask.objects.select_related(
            'workflow', 'assigned_to'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from datetime import date
        task = self.get_object()
        task.status = 'completed'
        task.completed_date = date.today()
        task.save(update_fields=['status', 'completed_date'])
        return Response({'data': ReorgWorkflowTaskSerializer(task).data})

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        task = self.get_object()
        task.status = 'blocked'
        task.blockers = request.data.get('blockers', task.blockers)
        task.save(update_fields=['status', 'blockers'])
        return Response({'data': ReorgWorkflowTaskSerializer(task).data})
