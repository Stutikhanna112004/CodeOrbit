from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .ai_service import get_ai_teach, get_ai_convert
import json
from .ai_service import get_ai_review
from .models import ReviewComment


from .models import CustomUser, Review
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
)
# We'll create this task in Phase 5 (Celery)
# from .tasks import process_review_task

from django.shortcuts import render, redirect
from django.views import View

class DashboardView(View):
    def get(self, request):
        return render(request, 'reviews/dashboard.html')

class LoginPageView(View):
    def get(self, request):
        return render(request, 'reviews/login.html')

class RegisterPageView(View):
    def get(self, request):
        return render(request, 'reviews/register.html')
    
class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Open to everyone — no token required.
    Creates a new user and returns their JWT tokens immediately.
    """
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # Override the global IsAuthenticated default

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens for the newly created user
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Account created successfully.',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            # Send both tokens so the frontend can log in immediately
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  → returns logged-in user's profile
    PUT  /api/auth/profile/  → updates bio etc.
    Requires valid JWT token.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Always return the currently logged-in user's profile
        return self.request.user


class ReviewViewSet(viewsets.ModelViewSet):
    """
    A ViewSet gives us all CRUD operations automatically:

    GET    /api/reviews/         → list all reviews for this user
    POST   /api/reviews/         → submit new code for review
    GET    /api/reviews/{id}/    → get one specific review
    DELETE /api/reviews/{id}/    → delete a review

    All endpoints require JWT authentication.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can ONLY see their own reviews — never other users'
        return Review.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        # Use the minimal serializer for creating, full one for reading
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        """
        Called automatically when POST /api/reviews/ is hit.
        """
        review = serializer.save(user=self.request.user)

     # Cast request.user to CustomUser so Pylance knows about our custom fields
        user = CustomUser.objects.get(pk=self.request.user.pk)
        user.total_reviews += 1
        user.save(update_fields=['total_reviews'])

     # Queue the AI review as a background task (Phase 5)
     # process_review_task.delay(review.id)

        return review

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        GET /api/reviews/stats/
        Returns summary stats for the logged-in user's dashboard.
        This is a custom endpoint — not part of default CRUD.
        """
        reviews = self.get_queryset()

        # Calculate average quality score (excluding null scores)
        completed = reviews.filter(status='completed')
        scores = [r.quality_score for r in completed if r.quality_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        return Response({
            'total_reviews': reviews.count(),
            'completed': completed.count(),
            'pending': reviews.filter(status='pending').count(),
            'failed': reviews.filter(status='failed').count(),
            'average_quality_score': avg_score,
            'languages_used': list(
                reviews.values_list('language', flat=True).distinct()
            ),
        })
    
class TriggerReviewView(generics.GenericAPIView):
    """
    POST /api/reviews/{id}/trigger/
    Manually triggers the AI review for a specific submission.
    Calls OpenAI, saves result to DB, returns the full review.

    In Phase 5 we'll replace this with Celery so it runs in background.
    For now this is synchronous — the request waits for AI to finish.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Get the review — make sure it belongs to this user
        review = get_object_or_404(Review, pk=pk, user=request.user)

        # Don't re-review something already completed
        if review.status == 'completed':
            return Response(
                {'error': 'This review is already completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark as processing so the frontend can show a spinner
        review.status = 'processing'
        review.save(update_fields=['status'])

        # ── Call the AI ───────────────────────────────────────────────
        result = get_ai_review(review.code_snippet, review.language)

        if not result['success']:
            # Something went wrong with the AI call
            review.status = 'failed'
            review.save(update_fields=['status'])
            return Response(
                {'error': result['error']},
                status=status.HTTP_502_BAD_GATEWAY
            )

        data = result['data']

        # ── Save AI feedback to the Review model ──────────────────────
        review.ai_feedback = json.dumps(data)         # Store full JSON
        review.quality_score = data.get('quality_score', 0)
        review.status = 'completed'
        review.save(update_fields=['ai_feedback', 'quality_score', 'status'])

        # ── Save each inline comment to ReviewComment model ───────────
        # Delete old comments first in case this is a re-review
        ReviewComment.objects.filter(review=review).delete()

        for comment in data.get('inline_comments', []):
            ReviewComment.objects.create(
                review=review,
                line_number=comment.get('line_number'),
                severity=comment.get('severity', 'info'),
                message=comment.get('message', ''),
                suggestion=comment.get('suggestion', ''),
            )

        # ── Return the full completed review ──────────────────────────
        serializer = ReviewSerializer(review)
        return Response({
            'review': serializer.data,
            'ai_data': data,   # Full structured AI response
        })

class TeachView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        concept  = request.data.get('concept', '').strip()
        language = request.data.get('language', 'python').strip()

        if not concept:
            return Response(
                {'error': 'Please provide a concept to learn.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = get_ai_teach(concept, language)
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_502_BAD_GATEWAY
            )
        return Response(result['data'])


class ConvertView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code      = request.data.get('code', '').strip()
        from_lang = request.data.get('from_lang', 'python')
        to_lang   = request.data.get('to_lang', 'javascript')

        if not code:
            return Response(
                {'error': 'Please provide code to convert.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = get_ai_convert(code, from_lang, to_lang)
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_502_BAD_GATEWAY
            )
        return Response(result['data'])