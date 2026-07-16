"""Admin for the structured-data validator."""
from django.contrib import admin

from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob


class SchemaIssueInline(admin.TabularInline):
    model = SchemaIssue
    extra = 0
    fields = ("severity", "field", "message", "suggestion")
    readonly_fields = fields
    can_delete = False
    show_change_link = False


class SchemaItemInline(admin.TabularInline):
    model = SchemaItem
    extra = 0
    fields = ("schema_type", "format", "is_valid", "google_rich_result_eligible")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(ValidationJob)
class ValidationJobAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "user",
        "status",
        "total_schemas_found",
        "total_errors",
        "total_warnings",
        "has_json_ld",
        "has_microdata",
        "has_rdfa",
        "created_at",
    )
    list_filter = ("status", "has_json_ld", "has_microdata", "has_rdfa", "is_deleted")
    search_fields = ("url", "user__email", "user__username")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    inlines = [SchemaItemInline]


@admin.register(SchemaItem)
class SchemaItemAdmin(admin.ModelAdmin):
    list_display = ("schema_type", "format", "is_valid", "google_rich_result_eligible", "job")
    list_filter = ("format", "is_valid", "google_rich_result_eligible")
    search_fields = ("schema_type", "job__url")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [SchemaIssueInline]


@admin.register(SchemaIssue)
class SchemaIssueAdmin(admin.ModelAdmin):
    list_display = ("severity", "field", "schema_item", "message")
    list_filter = ("severity",)
    search_fields = ("field", "message")
    readonly_fields = ("id", "created_at", "updated_at")
