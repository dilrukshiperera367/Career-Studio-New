"""
Custom exception handler for consistent HRM API error responses.

Standard error format:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "One or more fields failed validation.",
        "details": { "field_name": ["error message"] },
        "status": 400
    }
}
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

ERROR_CODES = {
    400: 'BAD_REQUEST',
    401: 'AUTHENTICATION_REQUIRED',
    403: 'PERMISSION_DENIED',
    404: 'NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED',
    409: 'CONFLICT',
    429: 'RATE_LIMIT_EXCEEDED',
    500: 'INTERNAL_SERVER_ERROR',
    503: 'SERVICE_UNAVAILABLE',
}


def custom_exception_handler(exc, context):
    """DRF exception handler — wraps all errors in a standard envelope."""
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in view %s", context.get('view'))
        return Response(
            {
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'An unexpected error occurred.',
                    'status': 500,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    status_code = response.status_code
    code = ERROR_CODES.get(status_code, 'API_ERROR')

    data = response.data
    if isinstance(data, dict):
        message = data.get('detail', data.get('message', 'An error occurred.'))
        if hasattr(message, 'code') and message.code:
            code = message.code.upper().replace(' ', '_')
        message = str(message)
        details = {k: v for k, v in data.items() if k not in ('detail', 'message')} or None
    elif isinstance(data, list):
        message = '; '.join(str(e) for e in data[:3])
        details = None
    else:
        message = str(data)
        details = None

    error_envelope = {
        'error': {
            'code': code,
            'message': message,
            'status': status_code,
        }
    }
    if details:
        error_envelope['error']['details'] = details

    response.data = error_envelope
    return response
