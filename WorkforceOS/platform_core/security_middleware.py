"""
Security middleware: CSP, security headers, rate limiting.
"""
import time
import hashlib
from django.http import JsonResponse
from django.utils.cache import patch_cache_control
from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Adds comprehensive security headers to all responses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Never cache API responses
        if request.path.startswith('/api/'):
            patch_cache_control(response, no_store=True, no_cache=True, must_revalidate=True)
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.stripe.com https://sentry.io; "
            "frame-src https://js.stripe.com; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        
        # Other security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['server'] = 'ConnectOS'  # Hide server info
        
        # HSTS in production
        if not getattr(settings, 'DEBUG', True):
            response['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        
        return response


class RateLimitMiddleware:
    """
    Simple in-process rate limiting using a sliding window.
    For production, replace with django-ratelimit + Redis.
    
    Limits:
    - Login/auth endpoints: 5 per minute per IP
    - Other API: 300 per minute per IP
    """
    
    # Simple in-memory store: {key: [(timestamp, count)]}
    _store = {}
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Only rate-limit API paths
        if not path.startswith('/api/'):
            return self.get_response(request)
        
        ip = self._get_ip(request)
        is_auth = '/auth/login' in path or '/auth/register' in path
        
        limit = 5 if is_auth else 300
        window = 60  # seconds
        
        if self._is_rate_limited(ip, path, limit, window, is_auth):
            return JsonResponse(
                {'error': 'rate_limit_exceeded', 'message': 'Too many requests. Please slow down.', 'retry_after': window},
                status=429
            )
        
        response = self.get_response(request)
        return response

    def _get_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _is_rate_limited(self, ip, path, limit, window, auth_endpoint):
        now = time.time()
        key = f"{'auth' if auth_endpoint else 'api'}:{ip}"
        
        # Clean old entries
        if key in self._store:
            self._store[key] = [t for t in self._store[key] if now - t < window]
        else:
            self._store[key] = []
        
        # Limit store size to prevent memory exhaustion
        if len(self._store) > 50000:
            self._store.clear()
        
        count = len(self._store[key])
        if count >= limit:
            return True
        
        self._store[key].append(now)
        return False


class InputSanitizationMiddleware:
    """
    Basic XSS protection on request inputs.
    """
    DANGEROUS_PATTERNS = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check body for dangerous patterns (POST/PATCH)
        if request.method in ('POST', 'PUT', 'PATCH') and request.content_type == 'application/json':
            body = request.body.decode('utf-8', errors='ignore').lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in body:
                    return JsonResponse(
                        {'error': 'invalid_input', 'message': 'Input contains disallowed content.'},
                        status=400
                    )
        return self.get_response(request)
