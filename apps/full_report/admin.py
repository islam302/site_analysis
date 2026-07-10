"""Admin for the full report jobs."""
from django.contrib import admin

from apps.full_report.models import FullReport


@admin.register(FullReport)
class FullReportAdmin(admin.ModelAdmin):
    list_display = ("url", "status", "strategy", "lang", "user", "created_at")
    list_filter = ("status", "strategy", "lang", "is_deleted")
    search_fields = ("url", "user__email", "user__username")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "tools_status", "file")
