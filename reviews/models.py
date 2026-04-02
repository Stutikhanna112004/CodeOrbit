from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    We extend Django's built-in User model so we can add extra fields later.
    AbstractUser already gives us: username, email, password, is_staff, etc.
    """
    bio = models.TextField(blank=True)
    total_reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class Review(models.Model):
    """
    One review = one code submission + one AI response.
    Linked to the user who submitted it.
    """

    # Supported programming languages
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('typescript', 'TypeScript'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('go', 'Go'),
        ('rust', 'Rust'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),      # Just submitted, waiting for AI
        ('processing', 'Processing'),# AI is currently reviewing
        ('completed', 'Completed'),  # AI finished, result is ready
        ('failed', 'Failed'),        # Something went wrong
    ]

    # ForeignKey means: one user can have many reviews
    # on_delete=CASCADE means: if user is deleted, their reviews are too
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews'  # lets us do user.reviews.all()
    )

    # The code the user submitted
    code_snippet = models.TextField()

    # What language it is
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)

    # The AI's full review (stored after completion)
    ai_feedback = models.TextField(blank=True)

    # Quality score from 0-100 that the AI assigns
    quality_score = models.PositiveSmallIntegerField(null=True, blank=True)

    # Current state of this review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Optional title the user gives their submission
    title = models.CharField(max_length=200, blank=True)

    # Timestamps — auto_now_add sets once on creation, auto_now updates every save
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Return newest reviews first by default
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.language} — {self.status}"


class ReviewComment(models.Model):
    """
    The AI breaks its feedback into individual inline comments.
    Each comment points to a specific line number in the code.
    """

    SEVERITY_CHOICES = [
        ('critical', 'Critical'),  # Security issue or major bug
        ('warning', 'Warning'),    # Should be fixed
        ('info', 'Info'),          # Suggestion / best practice
    ]

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments'  # lets us do review.comments.all()
    )

    line_number = models.PositiveIntegerField(null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    message = models.TextField()  # The AI's comment for this line
    suggestion = models.TextField(blank=True)  # Optional improved code

    class Meta:
        ordering = ['line_number']

    def __str__(self):
        return f"Line {self.line_number} — {self.severity}"