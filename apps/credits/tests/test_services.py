"""Tests for credit services, including deduction edge cases."""
import pytest

from apps.credits.constants import TransactionType
from apps.credits.exceptions import InsufficientCreditsError, InvalidCreditAmountError
from apps.credits.models import CreditBalance, CreditTransaction
from apps.credits.services import add_credits, check_balance, deduct_credit
from apps.credits.tests.factories import set_balance
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_balance_auto_created_for_new_user():
    user = UserFactory()
    assert CreditBalance.objects.filter(user=user).exists()
    assert user.credit_balance.balance == 0


# --- add --------------------------------------------------------------------
def test_add_credits_increases_balance_and_records_tx():
    user = UserFactory()
    tx = add_credits(user=user, amount=50, description="Top up")

    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 50
    assert user.credit_balance.total_purchased == 50
    assert tx.transaction_type == TransactionType.PURCHASE
    assert tx.amount == 50
    assert tx.balance_after == 50


def test_add_credits_rejects_non_positive():
    user = UserFactory()
    with pytest.raises(InvalidCreditAmountError):
        add_credits(user=user, amount=0)


# --- deduct -----------------------------------------------------------------
def test_deduct_credit_decrements_and_records_usage():
    user = UserFactory()
    set_balance(user, 3)

    tx = deduct_credit(user=user, amount=1, description="Audit")

    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 2
    assert user.credit_balance.total_used == 1
    assert tx.transaction_type == TransactionType.USAGE
    assert tx.amount == -1
    assert tx.balance_after == 2


def test_deduct_credit_zero_balance_raises():
    user = UserFactory()  # balance starts at 0
    with pytest.raises(InsufficientCreditsError):
        deduct_credit(user=user, amount=1)
    assert not CreditTransaction.objects.filter(user=user).exists()


def test_deduct_credit_exhausts_then_raises():
    """Deducting past zero raises and never drives the balance negative."""
    user = UserFactory()
    set_balance(user, 1)

    deduct_credit(user=user, amount=1)  # -> 0
    with pytest.raises(InsufficientCreditsError):
        deduct_credit(user=user, amount=1)  # -> would be negative

    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 0


def test_deduct_more_than_available_raises():
    user = UserFactory()
    set_balance(user, 2)
    with pytest.raises(InsufficientCreditsError):
        deduct_credit(user=user, amount=5)
    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 2  # unchanged


def test_deduct_negative_amount_raises():
    user = UserFactory()
    set_balance(user, 5)
    with pytest.raises(InvalidCreditAmountError):
        deduct_credit(user=user, amount=-1)


# --- check ------------------------------------------------------------------
def test_check_balance_ok():
    user = UserFactory()
    set_balance(user, 5)
    assert check_balance(user=user, required=3) == 5


def test_check_balance_insufficient_raises():
    user = UserFactory()
    with pytest.raises(InsufficientCreditsError):
        check_balance(user=user, required=1)
