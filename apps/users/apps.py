from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users & Authentication"

    def ready(self) -> None:
        # Register signal handlers.
        from apps.users import signals  # noqa: F401
