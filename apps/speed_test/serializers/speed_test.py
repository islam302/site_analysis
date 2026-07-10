"""Speed test serializers — combined Google PageSpeed + GTmetrix output."""
from rest_framework import serializers

from apps.analysis.constants import Strategy
from apps.analysis.serializers import AnalysisReportSerializer
from apps.common.validators import validate_http_url, validate_no_localhost
from apps.gtmetrix.serializers import GTmetrixReportSerializer
from apps.speed_test.models import SpeedTest


class SpeedTestInputSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )
    strategy = serializers.ChoiceField(choices=Strategy.choices, default=Strategy.MOBILE)


class SpeedTestSerializer(serializers.ModelSerializer):
    """Full combined result with both nested reports."""

    combined_status = serializers.CharField(read_only=True)
    google_report = AnalysisReportSerializer(read_only=True)
    gtmetrix_report = GTmetrixReportSerializer(read_only=True)

    class Meta:
        model = SpeedTest
        fields = [
            "id",
            "url",
            "strategy",
            "combined_status",
            "google_report",
            "gtmetrix_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SpeedTestListSerializer(serializers.ModelSerializer):
    """Compact combined representation for list endpoints."""

    combined_status = serializers.CharField(read_only=True)
    google_status = serializers.CharField(source="google_report.status", read_only=True, default=None)
    gtmetrix_status = serializers.CharField(
        source="gtmetrix_report.status", read_only=True, default=None
    )

    class Meta:
        model = SpeedTest
        fields = [
            "id",
            "url",
            "strategy",
            "combined_status",
            "google_status",
            "gtmetrix_status",
            "created_at",
        ]
        read_only_fields = fields
