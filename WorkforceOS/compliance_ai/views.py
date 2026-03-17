"""Compliance & AI Governance API views."""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import (
    AIModel,
    AIDecisionLog,
    PrivacyConsent,
    DataRetentionPolicy,
    AccessibilityConfig,
)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class AIModelSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class AIDecisionLogSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AIDecisionLog
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class PrivacyConsentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PrivacyConsent
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class DataRetentionPolicySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = DataRetentionPolicy
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class AccessibilityConfigSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AccessibilityConfig
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'updated_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class AIModelViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Full CRUD for AI model registry."""
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['model_type', 'is_active']
    search_fields = ['name', 'version']
    ordering_fields = ['name', 'created_at', 'last_trained_at']
    required_permissions = {
        'list': 'compliance_ai.manage_ai_models',
        'retrieve': 'compliance_ai.manage_ai_models',
        'create': 'compliance_ai.manage_ai_models',
        'update': 'compliance_ai.manage_ai_models',
        'partial_update': 'compliance_ai.manage_ai_models',
        'destroy': 'compliance_ai.manage_ai_models',
    }

    def get_queryset(self):
        return AIModel.objects.filter(tenant_id=self.request.tenant_id)


class AIDecisionLogViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only AI decision log with an override action."""
    queryset = AIDecisionLog.objects.select_related('ai_model').all()
    serializer_class = AIDecisionLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['ai_model', 'entity_type', 'was_overridden']
    ordering_fields = ['created_at', 'confidence_score']
    required_permissions = {
        'list': 'compliance_ai.view_ai_decisions',
        'retrieve': 'compliance_ai.view_ai_decisions',
        'override': 'compliance_ai.view_ai_decisions',
    }

    def get_queryset(self):
        return AIDecisionLog.objects.select_related(
            'ai_model'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def override(self, request, pk=None):
        """Mark an AI decision as overridden by the current user."""
        log = self.get_object()
        override_reason = request.data.get('override_reason', '')
        if not override_reason:
            return Response(
                {'error': 'override_reason is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log.was_overridden = True
        log.override_by = request.user
        log.override_reason = override_reason
        log.save(update_fields=['was_overridden', 'override_by', 'override_reason'])
        return Response(
            {'data': AIDecisionLogSerializer(log).data},
            status=status.HTTP_200_OK,
        )


class PrivacyConsentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Full CRUD for privacy consent records, plus my-consents action."""
    queryset = PrivacyConsent.objects.select_related('employee').all()
    serializer_class = PrivacyConsentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'consent_type', 'is_granted']
    ordering_fields = ['granted_at', 'withdrawn_at']
    required_permissions = {
        'list': 'compliance_ai.manage_privacy_consents',
        'retrieve': 'compliance_ai.manage_privacy_consents',
        'create': 'compliance_ai.manage_privacy_consents',
        'update': 'compliance_ai.manage_privacy_consents',
        'partial_update': 'compliance_ai.manage_privacy_consents',
        'destroy': 'compliance_ai.manage_privacy_consents',
        'my_consents': 'compliance_ai.manage_privacy_consents',
    }

    def get_queryset(self):
        return PrivacyConsent.objects.select_related(
            'employee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='my-consents')
    def my_consents(self, request):
        """Return all consent records for the currently authenticated employee."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response(
                {'error': 'No employee profile linked to this user.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        consents = self.get_queryset().filter(employee=employee)
        serializer = self.get_serializer(consents, many=True)
        return Response({'data': serializer.data})


class DataRetentionPolicyViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Full CRUD for data retention policies."""
    queryset = DataRetentionPolicy.objects.all()
    serializer_class = DataRetentionPolicySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['data_type', 'is_active']
    search_fields = ['data_type', 'legal_basis']
    ordering_fields = ['data_type', 'retention_years', 'next_purge_at']
    required_permissions = {
        'list': 'compliance_ai.manage_data_retention',
        'retrieve': 'compliance_ai.manage_data_retention',
        'create': 'compliance_ai.manage_data_retention',
        'update': 'compliance_ai.manage_data_retention',
        'partial_update': 'compliance_ai.manage_data_retention',
        'destroy': 'compliance_ai.manage_data_retention',
    }

    def get_queryset(self):
        return DataRetentionPolicy.objects.filter(tenant_id=self.request.tenant_id)


class AccessibilityConfigViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """Full CRUD for accessibility config, plus my-config GET/PATCH action."""
    queryset = AccessibilityConfig.objects.all()
    serializer_class = AccessibilityConfigSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['updated_at']
    required_permissions = {
        'list': 'compliance_ai.manage_accessibility',
        'retrieve': 'compliance_ai.manage_accessibility',
        'create': 'compliance_ai.manage_accessibility',
        'update': 'compliance_ai.manage_accessibility',
        'partial_update': 'compliance_ai.manage_accessibility',
        'destroy': 'compliance_ai.manage_accessibility',
        'my_config': 'compliance_ai.manage_accessibility',
    }

    def get_queryset(self):
        return AccessibilityConfig.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get', 'patch'], url_path='my-config')
    def my_config(self, request):
        """GET or PATCH the single accessibility config for this tenant."""
        config, _ = AccessibilityConfig.objects.get_or_create(
            tenant_id=request.tenant_id,
            defaults={},
        )
        if request.method == 'PATCH':
            serializer = self.get_serializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'data': serializer.data})
        return Response({'data': AccessibilityConfigSerializer(config).data})
