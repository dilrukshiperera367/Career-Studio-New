"""Global Workforce API views + serializers."""

from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import CountryPack, ExpatAssignment, VisaPermit, MultiCurrencyRate


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class CountryPackSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CountryPack
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class ExpatAssignmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ExpatAssignment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class VisaPermitSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = VisaPermit
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class MultiCurrencyRateSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = MultiCurrencyRate
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class CountryPackViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = CountryPack.objects.all()
    serializer_class = CountryPackSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['country_code', 'is_enabled']
    ordering_fields = ['country_name', 'country_code', 'created_at']
    required_permissions = {
        'list': 'global_workforce.manage_country_packs',
        'retrieve': 'global_workforce.manage_country_packs',
        'create': 'global_workforce.manage_country_packs',
        'update': 'global_workforce.manage_country_packs',
        'partial_update': 'global_workforce.manage_country_packs',
        'destroy': 'global_workforce.manage_country_packs',
    }

    def get_queryset(self):
        return CountryPack.objects.filter(tenant_id=self.request.tenant_id)


class ExpatAssignmentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ExpatAssignment.objects.select_related('employee').all()
    serializer_class = ExpatAssignmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'home_country', 'host_country', 'status']
    search_fields = [
        'employee__first_name', 'employee__last_name', 'employee__employee_number'
    ]
    ordering_fields = ['start_date', 'end_date', 'created_at']
    required_permissions = {
        'list': 'global_workforce.manage_expat',
        'retrieve': 'global_workforce.manage_expat',
        'create': 'global_workforce.manage_expat',
        'update': 'global_workforce.manage_expat',
        'partial_update': 'global_workforce.manage_expat',
        'destroy': 'global_workforce.manage_expat',
        'active': 'global_workforce.manage_expat',
    }

    def get_queryset(self):
        return ExpatAssignment.objects.select_related(
            'employee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Return assignments with status=active."""
        qs = self.get_queryset().filter(status='active')
        return Response({'data': ExpatAssignmentSerializer(qs, many=True).data})


class VisaPermitViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = VisaPermit.objects.select_related('employee').all()
    serializer_class = VisaPermitSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'permit_type', 'country', 'status']
    ordering_fields = ['expiry_date', 'issue_date', 'created_at']
    required_permissions = {
        'list': 'global_workforce.manage_visas',
        'retrieve': 'global_workforce.manage_visas',
        'create': 'global_workforce.manage_visas',
        'update': 'global_workforce.manage_visas',
        'partial_update': 'global_workforce.manage_visas',
        'destroy': 'global_workforce.manage_visas',
        'expiring_soon': 'global_workforce.manage_visas',
    }

    def get_queryset(self):
        return VisaPermit.objects.select_related(
            'employee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        """Return permits expiring within 90 days."""
        cutoff = timezone.now().date() + timedelta(days=90)
        qs = self.get_queryset().filter(
            expiry_date__lte=cutoff,
            expiry_date__gte=timezone.now().date(),
        ).order_by('expiry_date')
        return Response({'data': VisaPermitSerializer(qs, many=True).data})


class MultiCurrencyRateViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = MultiCurrencyRate.objects.all()
    serializer_class = MultiCurrencyRateSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['from_currency', 'to_currency', 'is_active']
    ordering_fields = ['effective_date', 'from_currency', 'to_currency']
    required_permissions = {
        'list': 'global_workforce.manage_currency_rates',
        'retrieve': 'global_workforce.manage_currency_rates',
        'create': 'global_workforce.manage_currency_rates',
        'update': 'global_workforce.manage_currency_rates',
        'partial_update': 'global_workforce.manage_currency_rates',
        'destroy': 'global_workforce.manage_currency_rates',
    }

    def get_queryset(self):
        return MultiCurrencyRate.objects.filter(tenant_id=self.request.tenant_id)
