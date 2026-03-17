"""Health check views — no authentication required."""

from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.views import View
import time


def health_check(request):
    """Liveness probe — always returns 200 if the process is alive."""
    return JsonResponse({"status": "ok", "service": "ats-backend"})


def readiness_check(request):
    """
    Readiness probe — checks database connectivity.
    Returns 200 if all dependencies are healthy, 503 otherwise.
    """
    checks = {}

    # Database check
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    # Overall status
    all_ok = all(c.get("status") == "ok" for c in checks.values())
    status_code = 200 if all_ok else 503

    return JsonResponse(
        {
            "status": "ok" if all_ok else "degraded",
            "service": "ats-backend",
            "version": "1.0.0",
            "debug": settings.DEBUG,
            "checks": checks,
        },
        status=status_code,
    )


class HealthCheckView(View):
    """
    Comprehensive health check for load balancer / monitoring:
    - Database connectivity
    - Cache (Redis) connectivity
    - Celery worker ping (optional)
    """

    def get(self, request):
        start = time.monotonic()
        checks = {}
        overall = 'healthy'

        # Database
        try:
            from django.db import connection as _conn
            _conn.ensure_connection()
            checks['database'] = {'status': 'healthy'}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'error': str(e)}
            overall = 'degraded'

        # Cache (Redis)
        try:
            from django.core.cache import cache
            cache.set('health_check_ping', 'pong', timeout=5)
            val = cache.get('health_check_ping')
            checks['cache'] = {'status': 'healthy' if val == 'pong' else 'degraded'}
        except Exception as e:
            checks['cache'] = {'status': 'unavailable', 'error': str(e)}
            # Cache unavailable is degraded, not unhealthy

        # Celery (optional — only if broker configured)
        try:
            broker = getattr(settings, 'CELERY_BROKER_URL', None)
            checks['celery'] = {
                'status': 'configured' if broker else 'not_configured',
                'broker': broker.split('@')[-1] if broker and '@' in broker else broker,
            }
        except Exception:
            checks['celery'] = {'status': 'unknown'}

        duration_ms = round((time.monotonic() - start) * 1000, 2)

        response_data = {
            'status': overall,
            'checks': checks,
            'duration_ms': duration_ms,
            'service': 'ConnectOS ATS',
        }

        http_status = 200 if overall == 'healthy' else 206
        return JsonResponse(response_data, status=http_status)
