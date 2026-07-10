"""Credit business logic.

All mutations lock the user's :class:`CreditBalance` row with
``select_for_update`` inside ``transaction.atomic`` so concurrent audits can
never double-spend or drive the balance negative.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.credits.constants import TransactionType
from apps.credits.exceptions import InsufficientCreditsError, InvalidCreditAmountError
from apps.credits.models import CreditBalance, CreditTransaction

logger = logging.getLogger("apps.credits")


def get_or_create_balance(*, user) -> CreditBalance:
    """Return the user's balance row, creating a zero balance if missing."""
    balance, _ = CreditBalance.objects.get_or_create(user=user)
    return balance


def check_balance(*, user, required: int = 1) -> int:
    """Return the user's current balance; raise if it is below ``required``.

    A read-only pre-flight check (fast fail). The authoritative check happens
    again under a row lock inside :func:`deduct_credit`.
    """
    balance = get_or_create_balance(user=user).balance
    if balance < required:
        raise InsufficientCreditsError(
            extra={"required": required, "balance": balance},
        )
    return balance


@transaction.atomic
def deduct_credit(*, user, amount: int = 1, description: str = "") -> CreditTransaction:
    """Atomically consume ``amount`` credits and record a usage transaction.

    Raises:
        InvalidCreditAmountError: if ``amount`` <= 0.
        InsufficientCreditsError: if the locked balance is below ``amount``.
    """
    if amount <= 0:
        raise InvalidCreditAmountError()

    balance = CreditBalance.objects.select_for_update().get(user=user)
    if balance.balance < amount:
        raise InsufficientCreditsError(
            extra={"required": amount, "balance": balance.balance},
        )

    balance.total_used += amount
    balance.balance -= amount
    balance.save(update_fields=["total_used", "balance", "updated_at"])

    tx = CreditTransaction.objects.create(
        user=user,
        amount=-amount,
        transaction_type=TransactionType.USAGE,
        description=description or "Credit usage",
        balance_after=balance.balance,
    )
    logger.info(
        "Credit deducted",
        extra={"user_id": str(user.id), "amount": amount, "balance_after": balance.balance},
    )
    return tx


@transaction.atomic
def add_credits(
    *,
    user,
    amount: int,
    description: str = "",
    transaction_type: str = TransactionType.PURCHASE,
) -> CreditTransaction:
    """Atomically add ``amount`` credits and record a purchase/refund transaction."""
    if amount <= 0:
        raise InvalidCreditAmountError()

    balance = CreditBalance.objects.select_for_update().get(user=user)
    if transaction_type == TransactionType.PURCHASE:
        balance.total_purchased += amount
    balance.balance += amount
    balance.save(update_fields=["total_purchased", "balance", "updated_at"])

    tx = CreditTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=transaction_type,
        description=description or "Credit purchase",
        balance_after=balance.balance,
    )
    logger.info(
        "Credits added",
        extra={"user_id": str(user.id), "amount": amount, "balance_after": balance.balance},
    )
    return tx
