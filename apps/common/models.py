"""Shared abstract models.

Every concrete model in the project inherits :class:`BaseModel`, giving it a
UUID primary key, audit timestamps, and soft-delete semantics. The default
manager hides soft-deleted rows; ``all_objects`` exposes them when needed.
"""
import uuid

from django.db import models
from django.utils import timezone


class BaseQuerySet(models.QuerySet):
    """QuerySet with soft-delete-aware helpers."""

    def active(self) -> "BaseQuerySet":
        return self.filter(is_deleted=False)

    def deleted(self) -> "BaseQuerySet":
        return self.filter(is_deleted=True)

    def soft_delete(self) -> int:
        """Bulk soft-delete; returns the number of affected rows."""
        return self.update(is_deleted=True, deleted_at=timezone.now())


class BaseManager(models.Manager):
    """Default manager that only returns non-deleted rows."""

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db)


class BaseModel(models.Model):
    """Abstract base for all models."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = BaseManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self) -> None:
        """Mark the row as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self) -> None:
        """Reverse a soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
