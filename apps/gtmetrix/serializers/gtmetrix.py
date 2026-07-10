"""GTmetrix serializers (plain input, ModelSerializer output)."""
from rest_framework import serializers

from apps.common.validators import validate_http_url, validate_no_localhost
from apps.gtmetrix.models import GTmetrixReport


class GTmetrixAnalyzeInputSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )


class GTmetrixReportSerializer(serializers.ModelSerializer):
    """Full report detail (includes raw_response)."""

    class Meta:
        model = GTmetrixReport
        fields = [
            "id",
            "url",
            "status",
            "error_message",
            "test_id",
            "report_url",
            "gtmetrix_grade",
            "performance_score",
            "structure_score",
            "first_contentful_paint",
            "largest_contentful_paint",
            "cumulative_layout_shift",
            "total_blocking_time",
            "time_to_interactive",
            "speed_index",
            "onload_time",
            "fully_loaded_time",
            "page_bytes",
            "page_requests",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GTmetrixReportListSerializer(serializers.ModelSerializer):
    """Compact representation for list endpoints (no raw_response)."""

    class Meta:
        model = GTmetrixReport
        fields = [
            "id",
            "url",
            "status",
            "gtmetrix_grade",
            "performance_score",
            "structure_score",
            "fully_loaded_time",
            "created_at",
        ]
        read_only_fields = fields
