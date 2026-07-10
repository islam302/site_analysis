from django.apps import AppConfig


class GTmetrixConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gtmetrix"
    verbose_name = "GTmetrix Analysis"

    def ready(self) -> None:
        from apps.gtmetrix import signals  # noqa: F401
