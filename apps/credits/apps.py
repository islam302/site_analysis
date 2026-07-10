from django.apps import AppConfig


class CreditsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.credits"
    verbose_name = "Credits & Quota"

    def ready(self) -> None:
        from apps.credits import signals  # noqa: F401
