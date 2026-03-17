"""Caching utilities for HRM."""
import hashlib
import logging
from functools import wraps
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache timeout constants
CACHE_SHORT = 60          # 1 minute
CACHE_MEDIUM = 300        # 5 minutes
CACHE_LONG = 3600         # 1 hour
CACHE_VERY_LONG = 86400   # 24 hours


def make_cache_key(*parts) -> str:
    """Build a namespaced cache key, hashed if too long."""
    key = ':'.join(str(p) for p in parts)
    if len(key) > 200:
        key = hashlib.md5(key.encode()).hexdigest()
    return key


def cache_result(timeout=CACHE_MEDIUM, key_prefix=''):
    """Decorator to cache the result of a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = make_cache_key(key_prefix or func.__name__, *args, *sorted(kwargs.items()))
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_tenant_cache(tenant_id: str, prefix: str = ''):
    """Invalidate all cache keys for a tenant."""
    # django-redis supports pattern deletion
    try:
        pattern = f'*{prefix}*{tenant_id}*'
        cache.delete_pattern(pattern)
    except Exception as e:
        logger.debug('Cache invalidation failed (non-critical): %s', e)


def get_or_set(key: str, callable_fn, timeout: int = CACHE_MEDIUM):
    """Get value from cache or compute and store it."""
    result = cache.get(key)
    if result is None:
        result = callable_fn()
        if result is not None:
            cache.set(key, result, timeout)
    return result
