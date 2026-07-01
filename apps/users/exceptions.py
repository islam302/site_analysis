"""Domain exceptions for the users app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class InvalidCredentialsError(ApplicationError):
    default_message = "Invalid email or password."
    default_status = status.HTTP_401_UNAUTHORIZED


class InactiveAccountError(ApplicationError):
    default_message = "This account is inactive."
    default_status = status.HTTP_403_FORBIDDEN


class EmailAlreadyRegisteredError(ApplicationError):
    default_message = "A user with this email already exists."
    default_status = status.HTTP_409_CONFLICT


class UsernameAlreadyTakenError(ApplicationError):
    default_message = "A user with this username already exists."
    default_status = status.HTTP_409_CONFLICT


class InvalidTokenError(ApplicationError):
    default_message = "The token is invalid or has expired."
    default_status = status.HTTP_400_BAD_REQUEST


class EmailAlreadyVerifiedError(ApplicationError):
    default_message = "This email address is already verified."
    default_status = status.HTTP_409_CONFLICT


class IncorrectPasswordError(ApplicationError):
    default_message = "The current password is incorrect."
    default_status = status.HTTP_400_BAD_REQUEST


class UserNotFoundError(ApplicationError):
    default_message = "User not found."
    default_status = status.HTTP_404_NOT_FOUND
