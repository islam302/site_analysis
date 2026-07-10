"""Domain exceptions for the speed_test app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class SpeedTestNotFoundError(ApplicationError):
    default_message = "Speed test not found."
    default_status = status.HTTP_404_NOT_FOUND
