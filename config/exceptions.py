from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'error': True,
            'status_code': response.status_code,
            'message': _get_error_message(response),
            'details': response.data,
        }
        response.data = error_data
    else:
        response = Response({
            'error': True,
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': 'Internal server error',
            'details': str(exc),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


def _get_error_message(response):
    status_code = response.status_code
    messages = {
        400: 'Bad request',
        401: 'Authentication required',
        403: 'Permission denied',
        404: 'Not found',
        405: 'Method not allowed',
        409: 'Conflict',
        429: 'Rate limit exceeded',
        500: 'Internal server error',
    }
    return messages.get(status_code, 'Error')
