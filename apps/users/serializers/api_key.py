"""API key and admin-facing user serializers (output only)."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import ApiKey

User = get_user_model()


class ApiKeySerializer(serializers.ModelSerializer):
    """Full API key — returned to the key's owner and to admins."""

    class Meta:
        model = ApiKey
        fields = ["id", "key", "is_active", "last_used_at", "created_at"]
        read_only_fields = fields


class AdminUserSerializer(serializers.ModelSerializer):
    """User representation for admins, including the user's API key."""

    api_key = ApiKeySerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "is_staff",
            "is_email_verified",
            "api_key",
            "created_at",
        ]
        read_only_fields = fields
