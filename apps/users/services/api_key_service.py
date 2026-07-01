"""API key business logic."""
from __future__ import annotations

import logging

from django.db import transaction

from apps.users.models import ApiKey

logger = logging.getLogger("apps.users")


def get_or_create_api_key(*, user) -> ApiKey:
    """Return the user's API key, creating one if it is somehow missing."""
    api_key, _ = ApiKey.objects.get_or_create(user=user)
    return api_key


@transaction.atomic
def rotate_api_key(*, user) -> ApiKey:
    """Generate a fresh key for the user, invalidating the previous one."""
    api_key = get_or_create_api_key(user=user)
    api_key.rotate()
    logger.info("API key rotated", extra={"user_id": str(user.id)})
    return api_key
