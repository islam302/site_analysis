"""Test helpers for the credits app.

A CreditBalance is auto-created for every user by a signal, so tests adjust the
existing balance rather than creating a new row.
"""
from apps.credits.models import CreditBalance


def set_balance(user, amount: int) -> CreditBalance:
    """Set a user's credit balance (and matching total_purchased) to ``amount``."""
    balance = user.credit_balance
    balance.balance = amount
    balance.total_purchased = amount
    balance.total_used = 0
    balance.save()
    return balance
