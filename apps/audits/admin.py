"""Admin for accessibility audit models."""
from django.contrib import admin

from apps.audits.models import AccessibilityAudit, AuditIssue


class AuditIssueInline(admin.TabularInline):
    model = AuditIssue
    extra = 0
    readonly_fields = ("issue_type", "wave_id", "description", "count", "wcag_reference")
    can_delete = False


@admin.register(AccessibilityAudit)
class AccessibilityAuditAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "status",
        "total_errors",
        "total_contrast_errors",
        "wcag_level",
        "credits_consumed",
        "user",
        "created_at",
    )
    list_filter = ("status", "wcag_level", "is_deleted")
    search_fields = ("url", "user__email", "user__username")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "raw_response")
    inlines = [AuditIssueInline]


@admin.register(AuditIssue)
class AuditIssueAdmin(admin.ModelAdmin):
    list_display = ("wave_id", "issue_type", "count", "audit", "created_at")
    list_filter = ("issue_type",)
    search_fields = ("wave_id", "description")
    readonly_fields = ("id", "created_at", "updated_at")
