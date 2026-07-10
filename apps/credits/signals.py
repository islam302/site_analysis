"""Auto-provision a CreditBalance when a user is created."""
import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.credits.models import CreditBalance

logger = logging.getLogger("apps.credits")
User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="credits_create_balance")
def create_credit_balance(sender, instance, created, **kwargs) -> None:
    if created:
        CreditBalance.objects.get_or_create(user=instance)
        logger.info("Credit balance provisioned", extra={"user_id": str(instance.id)})
