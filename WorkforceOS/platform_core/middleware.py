"""Platform Core middleware — audit logging and module gating."""

import logging
from django.utils import timezone
from platform_core.models import AuditLog

logger = logging.getLogger('hrm')


class AuditMiddleware:
    """
    Automatically creates audit log entries for data-mutating requests.
    Works with the AuditMixin on views to capture before/after state.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log audit entries that were attached during the request
        if hasattr(request, '_audit_entries'):
            for entry in request._audit_entries:
                try:
                    AuditLog.objects.create(
                        tenant_id=request.tenant_id,
                        user=request.user if request.user.is_authenticated else None,
                        action=entry['action'],
                        entity_type=entry['entity_type'],
                        entity_id=entry['entity_id'],
                        changes=entry.get('changes', {}),
                        ip_address=self._get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    )
                except Exception as e:
                    logger.error(f"Audit log creation failed: {e}")

        return response

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
