"""Domain exceptions for the credits app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class InsufficientCreditsError(ApplicationError):
    default_message = "You do not have enough credits for this operation."
    default_status = status.HTTP_402_PAYMENT_REQUIRED


class InvalidCreditAmountError(ApplicationError):
    default_message = "Credit amount must be a positive integer."
    default_status = status.HTTP_400_BAD_REQUEST
