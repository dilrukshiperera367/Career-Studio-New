"""Tenant-aware base classes for serializers and views."""

from rest_framework import serializers, viewsets, permissions, status
from rest_framework.response import Response
from core_hr.pagination import StandardResultsSetPagination


class TenantSerializerMixin:
    """Automatically sets tenant_id on create from request context."""
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'tenant_id') and request.tenant_id:
            validated_data['tenant_id'] = request.tenant_id
        return super().create(validated_data)


class TenantViewSetMixin:
    """Filters queryset to current tenant and injects tenant on create."""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request, 'tenant_id') and self.request.tenant_id:
            return qs.filter(tenant_id=self.request.tenant_id)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_update(self, serializer):
        serializer.save()


class AuditMixin:
    """
    Mixin for views to log mutations to the audit trail.
    Attaches _audit_entries to request for AuditMiddleware to persist.
    """
    def _log_audit(self, request, action, entity_type, entity_id, changes=None):
        if not hasattr(request, '_audit_entries'):
            request._audit_entries = []
        request._audit_entries.append({
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'changes': changes or {},
        })
