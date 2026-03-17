"""Enhanced health check for HRM system."""
import time
import logging
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class HealthCheckView(View):

    def get(self, request):
        start = time.monotonic()
        checks = {}
        overall = 'healthy'

        # Database
        try:
            from django.db import connection
            connection.ensure_connection()
            checks['database'] = {'status': 'healthy'}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'error': str(e)}
            overall = 'degraded'

        # Cache
        try:
            from django.core.cache import cache
            cache.set('hrm_health_ping', 'pong', timeout=5)
            val = cache.get('hrm_health_ping')
            checks['cache'] = {'status': 'healthy' if val == 'pong' else 'degraded'}
        except Exception as e:
            checks['cache'] = {'status': 'unavailable', 'error': str(e)}

        # Celery
        try:
            from django.conf import settings
            broker = getattr(settings, 'CELERY_BROKER_URL', None)
            checks['celery'] = {
                'status': 'configured' if broker else 'not_configured',
            }
        except Exception:
            checks['celery'] = {'status': 'unknown'}

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        return JsonResponse({
            'status': overall,
            'checks': checks,
            'duration_ms': duration_ms,
            'service': 'ConnectOS HRM',
        }, status=200 if overall == 'healthy' else 206)
