"""Domain exceptions for the structured-data validator."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class ValidationJobNotFoundError(ApplicationError):
    default_message = "Validation job not found."
    default_status = status.HTTP_404_NOT_FOUND


class PageFetchError(ApplicationError):
    default_message = "Could not fetch the page for validation."
    default_status = status.HTTP_400_BAD_REQUEST
