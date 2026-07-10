"""Read-only queries for credits."""
from __future__ import annotations

from django.db.models import QuerySet

from apps.credits.models import CreditBalance, CreditTransaction
from apps.credits.services.credit_service import get_or_create_balance


def get_balance(*, user) -> CreditBalance:
    """Return the user's credit balance (created on demand)."""
    return get_or_create_balance(user=user)


def get_transactions(*, user) -> QuerySet[CreditTransaction]:
    """Return the user's credit transaction ledger, newest first."""
    return CreditTransaction.objects.filter(user=user).order_by("-created_at")
