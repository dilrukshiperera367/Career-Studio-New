"""Middleware for Job Finder platform."""


class RequestLanguageMiddleware:
    """Set request.lang from Accept-Language header or user preference."""

    SUPPORTED = {"en", "si", "ta"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.GET.get("lang") or request.META.get("HTTP_ACCEPT_LANGUAGE", "en")[:2]
        if lang not in self.SUPPORTED:
            lang = "en"
        request.lang = lang
        return self.get_response(request)
