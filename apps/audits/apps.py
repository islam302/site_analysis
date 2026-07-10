from django.apps import AppConfig


class AuditsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audits"
    verbose_name = "Accessibility Audits"

    def ready(self) -> None:
        from apps.audits import signals  # noqa: F401
