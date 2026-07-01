"""Per-user API key for header-based authentication."""
import secrets

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel

API_KEY_PREFIX = "sk_"


def generate_api_key() -> str:
    """Return a new random API key string (prefix + URL-safe token)."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


class ApiKey(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_key",
    )
    key = models.CharField(max_length=80, unique=True, db_index=True, editable=False)
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API key"
        verbose_name_plural = "API keys"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.masked} ({self.user_id})"

    def save(self, *args, **kwargs) -> None:
        if not self.key:
            self.key = generate_api_key()
        super().save(*args, **kwargs)

    @property
    def masked(self) -> str:
        """A short, safe-to-log representation, e.g. ``sk_abcd…wxyz``."""
        if len(self.key) <= 12:
            return self.key
        return f"{self.key[:7]}…{self.key[-4:]}"

    def rotate(self) -> None:
        """Replace the key with a freshly generated one."""
        self.key = generate_api_key()
        self.is_active = True
        self.save(update_fields=["key", "is_active", "updated_at"])
