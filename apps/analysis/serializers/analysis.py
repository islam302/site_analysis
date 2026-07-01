"""Analysis serializers.

Input  -> plain ``Serializer`` subclasses (explicit validation).
Output -> ``ModelSerializer`` with explicit ``fields`` lists.
"""
from rest_framework import serializers

from apps.analysis.constants import Strategy
from apps.analysis.models import AnalysisHistory, AnalysisReport
from apps.common.validators import validate_http_url, validate_no_localhost

_URL_VALIDATORS = [validate_http_url, validate_no_localhost]


# --------------------------------------------------------------------------- #
# Input                                                                        #
# --------------------------------------------------------------------------- #
class AnalyzeInputSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048, validators=_URL_VALIDATORS)
    strategy = serializers.ChoiceField(
        choices=Strategy.choices,
        default=Strategy.MOBILE,
    )


# --------------------------------------------------------------------------- #
# Output                                                                       #
# --------------------------------------------------------------------------- #
class AnalysisReportSerializer(serializers.ModelSerializer):
    """Full report detail (includes raw_response)."""

    class Meta:
        model = AnalysisReport
        fields = [
            "id",
            "url",
            "strategy",
            "status",
            "error_message",
            "performance_score",
            "accessibility_score",
            "best_practices_score",
            "seo_score",
            "first_contentful_paint",
            "largest_contentful_paint",
            "total_blocking_time",
            "cumulative_layout_shift",
            "speed_index",
            "time_to_interactive",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AnalysisReportListSerializer(serializers.ModelSerializer):
    """Compact report representation for list endpoints (no raw_response)."""

    class Meta:
        model = AnalysisReport
        fields = [
            "id",
            "url",
            "strategy",
            "status",
            "performance_score",
            "accessibility_score",
            "best_practices_score",
            "seo_score",
            "created_at",
        ]
        read_only_fields = fields


class AnalysisHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisHistory
        fields = ["id", "url", "reports_count", "last_analyzed_at"]
        read_only_fields = fields
