from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
import redis
import os


def health_check(request):
    """Basic health check — confirms DB + Redis connectivity."""
    checks = {"status": "ok", "timestamp": timezone.now().isoformat()}

    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        checks["status"] = "degraded"

    # Redis
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=1)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        checks["status"] = "degraded"

    status_code = 200 if checks["status"] == "ok" else 503
    return JsonResponse(checks, status=status_code)
