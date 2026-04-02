"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from reviews.routing import websocket_urlpatterns
from reviews.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    # JWTAuthMiddleware reads ?token=... from the WebSocket URL
    'websocket': JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})