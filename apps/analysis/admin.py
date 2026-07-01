"""Django admin for analysis models."""
from django.contrib import admin

from apps.analysis.models import AnalysisHistory, AnalysisReport


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "strategy",
        "status",
        "performance_score",
        "accessibility_score",
        "best_practices_score",
        "seo_score",
        "user",
        "created_at",
    )
    list_filter = ("strategy", "status", "is_deleted")
    search_fields = ("url", "user__email")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "raw_response",
    )


@admin.register(AnalysisHistory)
class AnalysisHistoryAdmin(admin.ModelAdmin):
    list_display = ("url", "reports_count", "last_analyzed_at", "user")
    search_fields = ("url", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")
