from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Review, ReviewComment


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'total_reviews', 'created_at']

    # Cast to list first to avoid Pylance type mismatch with tuple concatenation
    fieldsets = list(UserAdmin.fieldsets) + [  # type: ignore[assignment]
        ('Profile', {'fields': ('bio', 'total_reviews')}),
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'language', 'status', 'quality_score', 'created_at']
    list_filter = ['status', 'language']   # Sidebar filters
    search_fields = ['user__username', 'title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ['review', 'line_number', 'severity']
    list_filter = ['severity']