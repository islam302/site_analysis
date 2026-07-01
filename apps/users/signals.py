"""Signal handlers for the users app."""
import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import ApiKey

logger = logging.getLogger("apps.users")
User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="users_user_created")
def on_user_created(sender, instance, created, **kwargs) -> None:
    """Audit-log new users and provision their API key exactly once."""
    if created:
        logger.info("User row created", extra={"user_id": str(instance.id)})
        ApiKey.objects.get_or_create(user=instance)
