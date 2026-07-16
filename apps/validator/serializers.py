"""Serializers for the structured-data validator."""
from rest_framework import serializers

from apps.common.validators import validate_http_url, validate_no_localhost
from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob


class SubmitValidationSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )


class SchemaIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaIssue
        fields = ["id", "severity", "field", "message", "suggestion", "created_at"]
        read_only_fields = fields


class SchemaItemSerializer(serializers.ModelSerializer):
    issues = SchemaIssueSerializer(many=True, read_only=True)

    class Meta:
        model = SchemaItem
        fields = [
            "id",
            "schema_type",
            "format",
            "is_valid",
            "google_rich_result_eligible",
            "raw_data",
            "issues",
            "created_at",
        ]
        read_only_fields = fields


class ValidationJobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationJob
        fields = [
            "id",
            "url",
            "status",
            "total_schemas_found",
            "total_errors",
            "total_warnings",
            "created_at",
        ]
        read_only_fields = fields


class ValidationJobSerializer(serializers.ModelSerializer):
    """Full job with every schema and its issues nested."""

    schemas = SchemaItemSerializer(many=True, read_only=True)

    class Meta:
        model = ValidationJob
        fields = [
            "id",
            "url",
            "status",
            "total_schemas_found",
            "total_errors",
            "total_warnings",
            "has_json_ld",
            "has_microdata",
            "has_rdfa",
            "error_message",
            "schemas",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
