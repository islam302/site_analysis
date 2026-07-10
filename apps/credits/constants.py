"""Constants for the credits app."""
from django.db import models


class TransactionType(models.TextChoices):
    PURCHASE = "purchase", "Purchase"
    USAGE = "usage", "Usage"
    REFUND = "refund", "Refund"
