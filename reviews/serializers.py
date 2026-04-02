from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Review, ReviewComment


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    We add password + confirm_password fields manually
    because they're not on the model directly.
    """
    password = serializers.CharField(
        write_only=True,          # Never send password back in response
        required=True,
        validators=[validate_password]  # Enforces Django's password rules
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'confirm_password']

    def validate(self, attrs):
        # Custom validation: make sure both passwords match
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        # Remove confirm_password — it's not a real model field
        validated_data.pop('confirm_password')

        # create_user handles password hashing automatically
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only snapshot of the logged-in user's profile.
    """
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'bio', 'total_reviews', 'created_at']
        read_only_fields = fields  # Nothing is editable via this serializer


class ReviewCommentSerializer(serializers.ModelSerializer):
    """
    Serializes individual AI inline comments tied to a review.
    """
    class Meta:
        model = ReviewComment
        fields = ['id', 'line_number', 'severity', 'message', 'suggestion']


class ReviewSerializer(serializers.ModelSerializer):
    """
    Full review serializer — includes nested comments and the username.
    Used when returning a completed review.
    """
    # Nest comments inside the review response automatically
    comments = ReviewCommentSerializer(many=True, read_only=True)

    # Show username instead of just user ID
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'username', 'title', 'language',
            'code_snippet', 'ai_feedback', 'quality_score',
            'status', 'comments', 'created_at', 'updated_at'
        ]
        # These fields are set by the server, not the user
        read_only_fields = ['ai_feedback', 'quality_score', 'status', 'username']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Minimal serializer just for submitting new code for review.
    User only sends: title, language, code_snippet.
    Everything else is filled in by the server.
    """
    class Meta:
        model = Review
        fields = ['id', 'title', 'language', 'code_snippet']