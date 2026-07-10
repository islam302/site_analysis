"""CreditTransaction: an immutable ledger entry for every credit change."""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.credits.constants import TransactionType


class CreditTransaction(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_transactions",
    )
    amount = models.IntegerField(help_text="Positive for credit added, negative for credit used.")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    balance_after = models.IntegerField(help_text="Balance snapshot immediately after this entry.")

    class Meta:
        verbose_name = "credit transaction"
        verbose_name_plural = "credit transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="credittx_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.amount:+d} (user {self.user_id})"
