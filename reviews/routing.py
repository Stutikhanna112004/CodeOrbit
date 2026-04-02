from django.urls import path
from .consumers import ReviewConsumer

websocket_urlpatterns = [
    # WebSocket connects to: ws://localhost:8000/ws/review/1/
    path('ws/review/<int:review_id>/', ReviewConsumer.as_asgi()),  # type: ignore[arg-type]
]
