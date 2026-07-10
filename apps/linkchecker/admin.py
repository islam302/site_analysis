"""Admin for the link checker."""
from django.contrib import admin

from apps.linkchecker.models import CrawlJob, LinkResult


class LinkResultInline(admin.TabularInline):
    model = LinkResult
    extra = 0
    fields = ("status_category", "link_type", "http_status", "target_url", "error_detail")
    readonly_fields = fields
    can_delete = False
    show_change_link = False


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "status",
        "total_links_found",
        "total_broken",
        "total_redirects",
        "total_timeouts",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("status", "is_deleted")
    search_fields = ("url",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    inlines = [LinkResultInline]


@admin.register(LinkResult)
class LinkResultAdmin(admin.ModelAdmin):
    list_display = ("target_url", "status_category", "link_type", "http_status", "crawl_job")
    list_filter = ("status_category", "link_type")
    search_fields = ("target_url", "source_url")
    readonly_fields = ("id", "created_at", "updated_at")
