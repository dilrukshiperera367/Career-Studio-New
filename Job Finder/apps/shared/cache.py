"""Shared caching utilities for API response caching (#186).

Provides a decorator for view-level caching using Redis/LocMem cache backend.
"""
import hashlib
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response


def cache_api_response(timeout=300, key_prefix="api"):
    """Cache DRF API view responses.

    Args:
        timeout: Cache TTL in seconds (default 5 min)
        key_prefix: Namespace prefix for cache keys
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Only cache GET requests
            if request.method != "GET":
                return view_func(self, request, *args, **kwargs)

            # Build cache key from URL + query params
            qs = request.META.get("QUERY_STRING", "")
            raw = f"{key_prefix}:{request.path}:{qs}"
            cache_key = hashlib.md5(raw.encode()).hexdigest()

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            response = view_func(self, request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            return response
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """Invalidate cache keys matching a pattern (Redis only)."""
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys(f"*{pattern}*")
        if keys:
            conn.delete(*keys)
    except (ImportError, Exception):
        # LocMem cache doesn't support pattern deletion
        pass
