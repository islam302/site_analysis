"""Admin for SSL reports."""
from django.contrib import admin

from apps.ssl_check.models import SSLReport


@admin.register(SSLReport)
class SSLReportAdmin(admin.ModelAdmin):
    list_display = (
        "host",
        "grade",
        "status",
        "has_warnings",
        "cert_expires_in_days",
        "cert_is_trusted",
        "user",
        "created_at",
    )
    list_filter = ("status", "grade", "has_warnings", "cert_is_trusted", "is_deleted")
    search_fields = ("host", "url", "user__email", "user__username")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "raw_response")
