"""Accessibility audit serializers."""
from rest_framework import serializers

from apps.audits.models import AccessibilityAudit, AuditIssue
from apps.common.validators import validate_http_url, validate_no_localhost


class RunAuditInputSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )


class AuditIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditIssue
        fields = [
            "id",
            "issue_type",
            "wave_id",
            "description",
            "count",
            "wcag_reference",
        ]
        read_only_fields = fields


class AuditListSerializer(serializers.ModelSerializer):
    """Compact audit representation for list endpoints (no raw_response/issues)."""

    class Meta:
        model = AccessibilityAudit
        fields = [
            "id",
            "url",
            "status",
            "total_errors",
            "total_alerts",
            "total_contrast_errors",
            "wcag_level",
            "credits_consumed",
            "created_at",
        ]
        read_only_fields = fields


class AuditSerializer(serializers.ModelSerializer):
    """Full audit detail including nested issues."""

    issues = AuditIssueSerializer(many=True, read_only=True)

    class Meta:
        model = AccessibilityAudit
        fields = [
            "id",
            "url",
            "status",
            "total_errors",
            "total_alerts",
            "total_features",
            "total_structural",
            "total_contrast_errors",
            "wcag_level",
            "credits_consumed",
            "error_message",
            "issues",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
