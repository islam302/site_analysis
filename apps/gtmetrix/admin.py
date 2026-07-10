"""Django admin for GTmetrix reports."""
from django.contrib import admin

from apps.gtmetrix.models import GTmetrixReport


@admin.register(GTmetrixReport)
class GTmetrixReportAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "status",
        "gtmetrix_grade",
        "performance_score",
        "structure_score",
        "fully_loaded_time",
        "user",
        "created_at",
    )
    list_filter = ("status", "gtmetrix_grade", "is_deleted")
    search_fields = ("url", "user__email", "test_id")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "raw_response", "test_id")
