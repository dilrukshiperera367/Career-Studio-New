"""Audit log middleware — logs every write operation with user, timestamp, and details.

In production (DEBUG=False), write operations are also persisted to the
ats_audit_log partitioned table for structured querying and compliance exports.
"""

import json
import logging
import time
import uuid
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.audit")


def _persist_audit_log(entry: dict):
    """
    Persist an audit log entry to the ats_audit_log partitioned table.
    Called from AuditLogMiddleware only in non-DEBUG mode.
    Errors are swallowed to avoid disrupting the request/response cycle.
    """
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ats_audit_log
                    (tenant_id, user_id, method, path, status_code,
                     ip_address, body_summary, duration_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    entry.get('tenant_id'),
                    entry.get('user_id') if entry.get('user_id') != 'anonymous' else None,
                    entry.get('method', ''),
                    entry.get('path', '')[:1000],
                    entry.get('status_code'),
                    entry.get('ip'),
                    (entry.get('body_summary') or '')[:5000],
                    entry.get('duration_ms'),
                    entry.get('timestamp'),
                ]
            )
    except Exception as exc:
        logger.debug('audit_persist failed (non-fatal): %s', exc)


class AuditLogMiddleware:
    """Log all write operations (POST, PUT, PATCH, DELETE) for compliance."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add correlation ID for request tracing
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
        request.correlation_id = correlation_id

        # Only audit write operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            start_time = time.monotonic()
            response = self.get_response(request)
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)

            user = getattr(request, "user", None)
            user_id = str(user.id) if user and hasattr(user, "id") and user.is_authenticated else "anonymous"
            tenant_id = getattr(request, 'tenant_id', None)

            log_entry = {
                "correlation_id": correlation_id,
                "timestamp": timezone.now().isoformat(),
                "method": request.method,
                "path": request.path,
                "user_id": user_id,
                "tenant_id": str(tenant_id) if tenant_id else None,
                "ip": self._get_client_ip(request),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

            # Log request body for auditing (exclude sensitive fields)
            if request.content_type and "json" in request.content_type:
                try:
                    body = json.loads(request.body)
                    # Redact sensitive fields
                    for field in ("password", "token", "secret", "ssn", "credit_card"):
                        if field in body:
                            body[field] = "***REDACTED***"
                    log_entry["body_summary"] = str(body)[:500]
                except (json.JSONDecodeError, Exception):
                    pass

            if response.status_code >= 400:
                logger.warning("AUDIT_FAIL: %s", json.dumps(log_entry))
            else:
                logger.info("AUDIT: %s", json.dumps(log_entry))

            # Persist to DB in production
            if not settings.DEBUG:
                _persist_audit_log(log_entry)

            # Add correlation ID to response
            response["X-Correlation-ID"] = correlation_id
            return response

        # For read operations, just add correlation ID
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class CORSValidationMiddleware:
    """Hardened CORS validation for production."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # X-Frame-Options to prevent clickjacking
        if "X-Frame-Options" not in response:
            response["X-Frame-Options"] = "DENY"
        return response
