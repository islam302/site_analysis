"""Serializers for the link checker."""
from rest_framework import serializers

from apps.common.validators import validate_http_url, validate_no_localhost
from apps.linkchecker.models import CrawlJob, LinkResult


class SubmitCrawlSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=2048,
        validators=[validate_http_url, validate_no_localhost],
    )
    crawl_depth = serializers.IntegerField(required=False, default=1, min_value=1, max_value=3)
    max_links = serializers.IntegerField(required=False, default=500, min_value=1, max_value=5000)
    render_js = serializers.BooleanField(required=False, default=False)


class CrawlJobSerializer(serializers.ModelSerializer):
    """Full crawl job with summary stats."""

    class Meta:
        model = CrawlJob
        fields = [
            "id",
            "url",
            "status",
            "total_links_found",
            "total_checked",
            "total_healthy",
            "total_broken",
            "total_redirects",
            "total_timeouts",
            "crawl_depth",
            "max_links",
            "render_js",
            "duration_seconds",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CrawlJobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlJob
        fields = [
            "id",
            "url",
            "status",
            "total_links_found",
            "total_broken",
            "created_at",
        ]
        read_only_fields = fields


class LinkResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkResult
        fields = [
            "id",
            "source_url",
            "target_url",
            "anchor_text",
            "link_type",
            "http_status",
            "status_category",
            "response_time_ms",
            "redirect_url",
            "error_detail",
            "created_at",
        ]
        read_only_fields = fields


class CrawlProgressSerializer(serializers.Serializer):
    status = serializers.CharField()
    total_links_found = serializers.IntegerField()
    total_checked = serializers.IntegerField()
    percent = serializers.FloatField()
