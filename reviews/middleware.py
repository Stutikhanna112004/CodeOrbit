from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import CustomUser


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate JWT token and return the user."""
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return CustomUser.objects.get(id=user_id)
    except (InvalidToken, TokenError, CustomUser.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that reads JWT token from WebSocket
    query string: ws://localhost:8000/ws/review/1/?token=eyJ...
    """
    async def __call__(self, scope, receive, send):
        # Parse token from query string
        from urllib.parse import parse_qs
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [])

        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])  # type: ignore
        else:
            scope['user'] = AnonymousUser()  # type: ignore

        return await super().__call__(scope, receive, send)