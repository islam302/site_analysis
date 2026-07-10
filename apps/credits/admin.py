"""Admin for credit models."""
from django.contrib import admin

from apps.credits.models import CreditBalance, CreditTransaction


@admin.register(CreditBalance)
class CreditBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "total_purchased", "total_used", "updated_at")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "transaction_type", "amount", "balance_after", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("user__username", "user__email", "description")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at")
