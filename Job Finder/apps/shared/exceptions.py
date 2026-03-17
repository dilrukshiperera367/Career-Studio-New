from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler that adds error codes and logging."""
    response = exception_handler(exc, context)

    if response is None:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return Response(
            {"error": "internal_server_error", "message": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(response.data, dict):
        response.data["status_code"] = response.status_code

    return response
