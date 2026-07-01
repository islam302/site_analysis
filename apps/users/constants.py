"""Constants for the users app."""
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    USER = "user", "User"


class EmailTokenScope(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "Email verification"


# Salt namespaces keep signed tokens for different purposes from being
# interchangeable even though they share SECRET_KEY.
EMAIL_VERIFICATION_SALT = "apps.users.email_verification"
