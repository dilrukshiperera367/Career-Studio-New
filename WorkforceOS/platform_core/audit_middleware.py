"""
Request/response audit logging middleware for HRM.
Logs all mutating API requests (POST/PUT/PATCH/DELETE) to the audit log table.
"""
import json
import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('hrm.audit')

# Paths to skip audit logging
SKIP_PATHS = {
    '/health/', '/ready/', '/api/schema/', '/api/docs/', '/api/redoc/',
    '/admin/jsi18n/', '/static/', '/media/',
}
MUTATING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class AuditLogMiddleware(MiddlewareMixin):
    """
    Logs all mutating API requests to the application audit log.
    Skips read-only requests and non-API paths.
    """

    def process_request(self, request):
        request._audit_start_time = time.monotonic()

    def process_response(self, request, response):
        if request.method not in MUTATING_METHODS:
            return response

        path = request.path_info
        if any(path.startswith(skip) for skip in SKIP_PATHS):
            return response

        if not path.startswith('/api/'):
            return response

        try:
            self._log_audit(request, response)
        except Exception as e:
            logger.debug('Audit log failed (non-critical): %s', e)

        return response

    def _log_audit(self, request, response):
        duration_ms = None
        if hasattr(request, '_audit_start_time'):
            duration_ms = int((time.monotonic() - request._audit_start_time) * 1000)

        user = getattr(request, 'user', None)
        user_id = str(user.id) if user and user.is_authenticated else None
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and user and user.is_authenticated:
            tenant_id = str(getattr(user, 'tenant_id', '') or '')

        # Safe body parsing
        request_body = {}
        if request.content_type and 'application/json' in request.content_type:
            try:
                request_body = json.loads(request.body.decode('utf-8', errors='ignore'))
                # Redact sensitive fields
                for field in ('password', 'token', 'secret', 'credit_card', 'card_number', 'cvv'):
                    if field in request_body:
                        request_body[field] = '***REDACTED***'
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'user_id': user_id,
            'tenant_id': str(tenant_id) if tenant_id else None,
            'ip': _get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'duration_ms': duration_ms,
        }

        if response.status_code >= 400:
            logger.warning('API %s %s → %d  user=%s tenant=%s ip=%s (%dms)',
                           request.method, request.path, response.status_code,
                           user_id, tenant_id, log_data['ip'], duration_ms or 0)
        else:
            logger.info('API %s %s → %d  user=%s tenant=%s (%dms)',
                        request.method, request.path, response.status_code,
                        user_id, tenant_id, duration_ms or 0)


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
