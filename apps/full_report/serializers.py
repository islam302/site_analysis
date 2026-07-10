"""Serializers for the combined full report."""
from rest_framework import serializers

from apps.analysis.constants import Strategy
from apps.common.validators import validate_http_url, validate_no_localhost
from apps.full_report.models import FullReport


class FullReportInputSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )
    strategy = serializers.ChoiceField(choices=Strategy.choices, default=Strategy.MOBILE)
    lang = serializers.ChoiceField(choices=[("en", "English"), ("ar", "Arabic")], default="en")


class FullReportSerializer(serializers.ModelSerializer):
    """Job status + a ``download_url`` for the PDF once completed."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FullReport
        fields = [
            "id",
            "url",
            "strategy",
            "lang",
            "status",
            "tools_status",
            "download_url",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: FullReport) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url
