import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Review, ReviewComment
from .ai_service import get_ai_review_stream


class ReviewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that streams AI code review to the browser.

    Lifecycle:
    1. Browser opens WebSocket connection to ws://localhost:8000/ws/review/{id}/
    2. connect() is called — we verify the user owns this review
    3. Browser sends {"action": "start_review"}
    4. receive() is called — we start streaming AI response chunk by chunk
    5. Each chunk is sent to browser instantly via send()
    6. When done, we save the full result to PostgreSQL
    7. disconnect() is called when browser closes the connection
    """

    async def connect(self):
        # Get review ID from the URL pattern
        url_route = self.scope.get('url_route', {})
        self.review_id = url_route.get('kwargs', {}).get('review_id')
        self.room_group_name = f'review_{self.review_id}'

        # scope['user'] is set by AuthMiddlewareStack in asgi.py
        user = self.scope.get('user')

        # Reject anonymous users — no token, no WebSocket
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify this review belongs to the connecting user
        review = await self.get_review(self.review_id, user)
        if not review:
            await self.close(code=4004)
            return

        self.review = review

        # Join the channel group for this review
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

        # Tell the browser we're connected and ready
        await self.send(json.dumps({
            'type': 'connected',
            'message': 'Connected. Send {"action": "start_review"} to begin.',
            'review_id': self.review_id,
        }))

    async def disconnect(self, close_code):
        # Clean up the channel group when browser disconnects
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Called when browser sends a message over the WebSocket.
        We only handle one action: 'start_review'
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(json.dumps({'type': 'error', 'message': 'Invalid JSON'}))
            return

        if data.get('action') == 'start_review':
            await self.stream_review()

    async def stream_review(self):
        """
        The main streaming method.
        Calls Gemini with stream=True and sends each chunk to the browser.
        """
        # Update review status to processing
        await self.update_review_status('processing')

        # Tell the browser streaming is starting
        await self.send(json.dumps({
            'type': 'stream_start',
            'message': 'AI review starting...',
        }))

        full_response = ''  # Accumulate the full response to save later

        try:
            # get_ai_review_stream is a generator — yields chunks
            # We run it in a thread because it's synchronous I/O
            loop = asyncio.get_event_loop()

            def run_stream():
                """Collect all chunks from the generator."""
                return list(get_ai_review_stream(
                    self.review.code_snippet,
                    self.review.language
                ))

            # Run the blocking generator in a thread pool
            chunks = await loop.run_in_executor(None, run_stream)

            # Stream each chunk to the browser with a tiny delay
            # This creates the typewriter effect
            for chunk in chunks:
                full_response += chunk
                await self.send(json.dumps({
                    'type': 'stream_chunk',
                    'chunk': chunk,
                }))
                # Small delay makes streaming feel more natural
                await asyncio.sleep(0.01)

            # ── Streaming complete — now save to database ─────────────
            await self.send(json.dumps({
                'type': 'stream_end',
                'message': 'Review complete. Saving...',
            }))

            # Parse and save the full response
            saved_data = await self.save_review_result(full_response)

            # Send the final structured data to the browser
            await self.send(json.dumps({
                'type': 'review_complete',
                'quality_score': saved_data.get('quality_score', 0),
                'summary': saved_data.get('summary', ''),
                'categories': saved_data.get('categories', {}),
                'inline_comments': saved_data.get('inline_comments', []),
                'positive_aspects': saved_data.get('positive_aspects', []),
                'improved_code': saved_data.get('improved_code', ''),
            }))

        except Exception as e:
            # Something went wrong — tell the browser and mark as failed
            await self.update_review_status('failed')
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Review failed: {str(e)}',
            }))

    @database_sync_to_async
    def get_review(self, review_id, user):
        """
        database_sync_to_async wraps synchronous Django ORM calls
        so they can be safely called from async code.
        """
        try:
            return Review.objects.get(id=review_id, user=user)
        except Review.DoesNotExist:
            return None

    @database_sync_to_async
    def update_review_status(self, status):
        Review.objects.filter(id=self.review_id).update(status=status)

    @database_sync_to_async
    def save_review_result(self, full_response):
        """
        Parses the accumulated JSON string and saves everything to DB.
        Returns the parsed data dict.
        """
        import json as json_module

        # Clean up any markdown formatting Gemini might add
        clean = full_response.strip()
        if clean.startswith('```'):
            clean = clean.split('\n', 1)[1]
        if clean.endswith('```'):
            clean = clean.rsplit('```', 1)[0]

        try:
            data = json_module.loads(clean)
        except json_module.JSONDecodeError:
            # If JSON parsing fails, save raw response
            data = {'summary': full_response, 'quality_score': 0}

        # Save to Review model
        Review.objects.filter(id=self.review_id).update(
            ai_feedback=json_module.dumps(data),
            quality_score=data.get('quality_score', 0),
            status='completed',
        )

        # Save inline comments
        ReviewComment.objects.filter(review_id=self.review_id).delete()
        for comment in data.get('inline_comments', []):
            ReviewComment.objects.create(
                review_id=self.review_id,
                line_number=comment.get('line_number'),
                severity=comment.get('severity', 'info'),
                message=comment.get('message', ''),
                suggestion=comment.get('suggestion', ''),
            )

        return data