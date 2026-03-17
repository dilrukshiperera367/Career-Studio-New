from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def health_check(request):
    return JsonResponse({"status": "ok", "service": "jobfinder-backend"})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "service": "ConnectOS Job Finder API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth/",
            "jobs": "/api/v1/jobs/",
            "candidates": "/api/v1/candidates/",
            "employers": "/api/v1/employers/",
            "applications": "/api/v1/applications/",
            "taxonomy": "/api/v1/taxonomy/",
            "search": "/api/v1/search/",
            "reviews": "/api/v1/reviews/",
            "notifications": "/api/v1/notifications/",
            "ats_connector": "/api/v1/ats-connector/",
        },
    })
