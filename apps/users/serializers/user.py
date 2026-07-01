"""User output & profile-update serializers."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public-facing representation of a user (output only)."""

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
            "is_email_verified",
            "is_staff",
            "created_at",
        ]
        read_only_fields = fields


class UpdateProfileSerializer(serializers.Serializer):
    """Input serializer for PATCH /auth/me/ — only mutable profile fields."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")
        return attrs
