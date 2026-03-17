"""Security middleware for production hardening."""

import time
import logging
import hashlib
import hmac
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""

    def process_response(self, request, response):
        # Prevent MIME-type sniffing
        response["X-Content-Type-Options"] = "nosniff"
        # XSS protection
        response["X-XSS-Protection"] = "1; mode=block"
        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Content Security Policy
        if not settings.DEBUG:
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://fonts.gstatic.com; "
                "connect-src 'self'"
            )
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log every API request for audit trail."""

    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, "_start_time"):
            duration_ms = (time.time() - request._start_time) * 1000
            if request.path.startswith("/api/"):
                log_data = {
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "user": str(getattr(request, "user", "anonymous")),
                    "ip": self._get_client_ip(request),
                }
                if response.status_code >= 400:
                    logger.warning("API request: %(method)s %(path)s -> %(status)s (%(duration_ms)sms)", log_data)
                else:
                    logger.info("API request: %(method)s %(path)s -> %(status)s (%(duration_ms)sms)", log_data)
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class LoginThrottleMiddleware(MiddlewareMixin):
    """Rate-limit login attempts by IP to prevent brute force (Redis-backed)."""

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 300   # 5 minutes
    LOCKOUT_SECONDS = 900  # 15 minutes

    LOGIN_PATHS = ("/api/v1/auth/login/", "/api/v1/auth/token/")

    def process_request(self, request):
        if request.path in self.LOGIN_PATHS and request.method == "POST":
            ip = self._get_ip(request)
            lockout_key = f"login_lockout:{ip}"
            attempt_key = f"login_throttle:{ip}"

            # Check active lockout
            locked_until = cache.get(lockout_key)
            if locked_until is not None:
                remaining = int(locked_until - time.time())
                if remaining > 0:
                    return JsonResponse(
                        {"error": f"Too many login attempts. Try again in {remaining} seconds."},
                        status=429,
                    )
                else:
                    cache.delete(lockout_key)
                    cache.delete(attempt_key)

    def process_response(self, request, response):
        if request.path in self.LOGIN_PATHS and request.method == "POST":
            ip = self._get_ip(request)
            lockout_key = f"login_lockout:{ip}"
            attempt_key = f"login_throttle:{ip}"

            if response.status_code in (400, 401):
                # Increment attempt count; set TTL on first attempt
                count = cache.get(attempt_key, 0)
                count += 1
                cache.set(attempt_key, count, timeout=self.WINDOW_SECONDS)
                if count >= self.MAX_ATTEMPTS:
                    # Impose lockout — store the expiry timestamp
                    cache.set(lockout_key, time.time() + self.LOCKOUT_SECONDS, timeout=self.LOCKOUT_SECONDS)
                    cache.delete(attempt_key)
            elif response.status_code == 200:
                # Successful login — clear counters
                cache.delete(attempt_key)
                cache.delete(lockout_key)
        return response

    @staticmethod
    def _get_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
