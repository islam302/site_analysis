"""Django admin for combined speed tests."""
from django.contrib import admin

from apps.speed_test.models import SpeedTest


@admin.register(SpeedTest)
class SpeedTestAdmin(admin.ModelAdmin):
    list_display = ("url", "strategy", "combined_status", "user", "created_at")
    list_filter = ("strategy", "is_deleted")
    search_fields = ("url", "user__email")
    autocomplete_fields = ("user", "google_report", "gtmetrix_report")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "combined_status")
