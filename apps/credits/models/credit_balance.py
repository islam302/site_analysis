"""CreditBalance: a user's running credit total."""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class CreditBalance(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_balance",
    )
    total_purchased = models.IntegerField(default=0)
    total_used = models.IntegerField(default=0)
    # Kept in sync with (total_purchased - total_used) on every credit operation
    # so it can be read/filtered without recomputation.
    balance = models.IntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = "credit balance"
        verbose_name_plural = "credit balances"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="balance_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.balance} credits"
