"""People Analytics API views — attrition risk, headcount, turnover, diversity, reports."""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import (
    AttritionRiskScore,
    HeadcountSnapshot,
    TurnoverReport,
    DiversityMetric,
    PeopleAnalyticsReport,
)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class AttritionRiskScoreSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AttritionRiskScore
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class HeadcountSnapshotSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = HeadcountSnapshot
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class TurnoverReportSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TurnoverReport
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class DiversityMetricSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = DiversityMetric
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class PeopleAnalyticsReportSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PeopleAnalyticsReport
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class AttritionRiskScoreViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only: attrition risk scores, filterable by employee/risk_level/is_current."""
    queryset = AttritionRiskScore.objects.select_related('employee', 'tenant').all()
    serializer_class = AttritionRiskScoreSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'risk_level', 'is_current']
    ordering_fields = ['computed_date', 'risk_score']
    required_permissions = {
        'list': 'people_analytics.view_attrition',
        'retrieve': 'people_analytics.view_attrition',
    }

    def get_queryset(self):
        return AttritionRiskScore.objects.select_related(
            'employee', 'tenant'
        ).filter(tenant_id=self.request.tenant_id)


class HeadcountSnapshotViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only: headcount snapshots, filterable by department/company/snapshot_date."""
    queryset = HeadcountSnapshot.objects.select_related('department', 'company').all()
    serializer_class = HeadcountSnapshotSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['department', 'company', 'snapshot_date']
    ordering_fields = ['snapshot_date', 'headcount']
    required_permissions = {
        'list': 'people_analytics.view_headcount',
        'retrieve': 'people_analytics.view_headcount',
    }

    def get_queryset(self):
        return HeadcountSnapshot.objects.select_related(
            'department', 'company'
        ).filter(tenant_id=self.request.tenant_id)


class TurnoverReportViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only: turnover reports, filterable by period_year/period_month/department."""
    queryset = TurnoverReport.objects.select_related('department').all()
    serializer_class = TurnoverReportSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['period_year', 'period_month', 'department']
    ordering_fields = ['period_year', 'period_month', 'turnover_rate']
    required_permissions = {
        'list': 'people_analytics.view_turnover',
        'retrieve': 'people_analytics.view_turnover',
    }

    def get_queryset(self):
        return TurnoverReport.objects.select_related(
            'department'
        ).filter(tenant_id=self.request.tenant_id)


class DiversityMetricViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only: diversity metrics, filterable by metric_type/scope_department."""
    queryset = DiversityMetric.objects.select_related('scope_department').all()
    serializer_class = DiversityMetricSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['metric_type', 'scope_department']
    ordering_fields = ['metric_date', 'total_count']
    required_permissions = {
        'list': 'people_analytics.view_diversity',
        'retrieve': 'people_analytics.view_diversity',
    }

    def get_queryset(self):
        return DiversityMetric.objects.select_related(
            'scope_department'
        ).filter(tenant_id=self.request.tenant_id)


class PeopleAnalyticsReportViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Full CRUD for saved analytics reports, plus a POST 'run' action."""
    queryset = PeopleAnalyticsReport.objects.all()
    serializer_class = PeopleAnalyticsReportSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['report_type', 'schedule', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'last_run_at']
    required_permissions = {
        'list': 'people_analytics.manage_reports',
        'retrieve': 'people_analytics.manage_reports',
        'create': 'people_analytics.manage_reports',
        'update': 'people_analytics.manage_reports',
        'partial_update': 'people_analytics.manage_reports',
        'destroy': 'people_analytics.manage_reports',
        'run': 'people_analytics.manage_reports',
    }

    def get_queryset(self):
        return PeopleAnalyticsReport.objects.filter(
            tenant_id=self.request.tenant_id
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """Trigger the report and return last_result."""
        report = self.get_object()
        # last_result may be populated by a background task in production;
        # here we return whatever is stored.
        return Response(
            {
                'data': {
                    'report_id': str(report.id),
                    'last_run_at': report.last_run_at,
                    'last_result': report.last_result,
                }
            },
            status=status.HTTP_200_OK,
        )
