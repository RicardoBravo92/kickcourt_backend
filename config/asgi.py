"""
ASGI config for config project.

Serves both HTTP (Django) and WebSocket (Channels) traffic.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        # Origin validation is handled per-consumer (see realtime.auth).
        'websocket': URLRouter(websocket_urlpatterns),
    }
)