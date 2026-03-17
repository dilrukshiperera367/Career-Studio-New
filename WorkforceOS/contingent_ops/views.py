"""Contingent Workforce Operations API views + serializers."""

from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import Vendor, ContingentWorker, ContingentTimesheet, ContingentCompliance


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class VendorSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class ContingentWorkerSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = ContingentWorker
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class ContingentTimesheetSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContingentTimesheet
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class ContingentComplianceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContingentCompliance
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class VendorViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['compliance_status', 'is_active']
    search_fields = ['name', 'legal_name']
    ordering_fields = ['name', 'created_at', 'compliance_status']
    required_permissions = {
        'list': 'contingent_ops.manage_vendors',
        'retrieve': 'contingent_ops.manage_vendors',
        'create': 'contingent_ops.manage_vendors',
        'update': 'contingent_ops.manage_vendors',
        'partial_update': 'contingent_ops.manage_vendors',
        'destroy': 'contingent_ops.manage_vendors',
    }

    def get_queryset(self):
        return Vendor.objects.filter(tenant_id=self.request.tenant_id)


class ContingentWorkerViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ContingentWorker.objects.select_related('vendor', 'department', 'manager').all()
    serializer_class = ContingentWorkerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['worker_type', 'vendor', 'department', 'manager', 'status']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['first_name', 'last_name', 'start_date', 'created_at']
    required_permissions = {
        'list': 'contingent_ops.manage_contingent_workers',
        'retrieve': 'contingent_ops.manage_contingent_workers',
        'create': 'contingent_ops.manage_contingent_workers',
        'update': 'contingent_ops.manage_contingent_workers',
        'partial_update': 'contingent_ops.manage_contingent_workers',
        'destroy': 'contingent_ops.manage_contingent_workers',
        'active': 'contingent_ops.manage_contingent_workers',
    }

    def get_queryset(self):
        return ContingentWorker.objects.select_related(
            'vendor', 'department', 'manager'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Return workers with status=active."""
        qs = self.get_queryset().filter(status='active')
        return Response({'data': ContingentWorkerSerializer(qs, many=True).data})


class ContingentTimesheetViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ContingentTimesheet.objects.select_related('worker').all()
    serializer_class = ContingentTimesheetSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['worker', 'status']
    ordering_fields = ['week_start', 'created_at', 'total_hours']
    required_permissions = {
        'list': 'contingent_ops.manage_timesheets',
        'retrieve': 'contingent_ops.manage_timesheets',
        'create': 'contingent_ops.manage_timesheets',
        'update': 'contingent_ops.manage_timesheets',
        'partial_update': 'contingent_ops.manage_timesheets',
        'destroy': 'contingent_ops.manage_timesheets',
        'approve': 'contingent_ops.manage_timesheets',
    }

    def get_queryset(self):
        return ContingentTimesheet.objects.select_related(
            'worker'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a submitted timesheet."""
        timesheet = self.get_object()
        timesheet.status = 'approved'
        timesheet.approved_by = request.user
        timesheet.approved_at = timezone.now()
        timesheet.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response({'data': ContingentTimesheetSerializer(timesheet).data})


class ContingentComplianceViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ContingentCompliance.objects.select_related('worker').all()
    serializer_class = ContingentComplianceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['worker', 'requirement_type', 'status']
    ordering_fields = ['expiry_date', 'created_at']
    required_permissions = {
        'list': 'contingent_ops.manage_compliance',
        'retrieve': 'contingent_ops.manage_compliance',
        'create': 'contingent_ops.manage_compliance',
        'update': 'contingent_ops.manage_compliance',
        'partial_update': 'contingent_ops.manage_compliance',
        'destroy': 'contingent_ops.manage_compliance',
        'expiring_soon': 'contingent_ops.manage_compliance',
    }

    def get_queryset(self):
        return ContingentCompliance.objects.select_related(
            'worker'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        """Return compliance records expiring within 60 days."""
        cutoff = timezone.now().date() + timedelta(days=60)
        qs = self.get_queryset().filter(
            expiry_date__lte=cutoff,
            expiry_date__gte=timezone.now().date(),
        ).order_by('expiry_date')
        return Response({'data': ContingentComplianceSerializer(qs, many=True).data})
