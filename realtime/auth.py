from urllib.parse import parse_qs

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


def get_user_from_scope(scope):
    """Resolve the JWT-authenticated user from the ``?token=`` query param.

    Browsers cannot set headers on a WebSocket, so the access token travels
    as a query parameter. Anonymous connections simply get ``None``.
    """
    query_string = scope.get('query_string', b'')
    params = parse_qs(query_string.decode('utf-8', errors='ignore'))
    token = (params.get('token') or [None])[0]
    if not token:
        return None
    try:
        access = AccessToken(token)
        user_id = access.get('user_id')
        if not user_id:
            return None
        return User.objects.filter(pk=user_id, is_active=True).first()
    except TokenError:
        return None


def is_allowed_origin(scope):
    """Reject browser websocket handshakes from unknown origins.

    Native/mobile clients (and tests) do not send an Origin header, so a
    missing Origin is allowed. Browser origins must be in CORS_ALLOWED_ORIGINS.
    """
    headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope.get('headers', [])}
    origin = headers.get('origin')
    if not origin:
        return True
    allowed = getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or []
    return any(origin.rstrip('/') == o.rstrip('/') for o in allowed)