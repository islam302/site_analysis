"""SSL check serializers."""
from rest_framework import serializers

from apps.common.validators import validate_http_url, validate_no_localhost
from apps.ssl_check.models import SSLReport


class SSLAnalyzeInputSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )


class SSLReportSerializer(serializers.ModelSerializer):
    """Full report detail (includes raw_response)."""

    class Meta:
        model = SSLReport
        fields = [
            "id",
            "url",
            "host",
            "status",
            "error_message",
            "grade",
            "has_warnings",
            "ip_address",
            "server_name",
            "cert_subject",
            "cert_issuer",
            "cert_valid_from",
            "cert_valid_to",
            "cert_expires_in_days",
            "cert_is_trusted",
            "protocols",
            "vulnerabilities",
            "raw_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SSLReportListSerializer(serializers.ModelSerializer):
    """Compact representation for list endpoints (no raw_response)."""

    class Meta:
        model = SSLReport
        fields = [
            "id",
            "url",
            "host",
            "status",
            "grade",
            "has_warnings",
            "cert_expires_in_days",
            "created_at",
        ]
        read_only_fields = fields
