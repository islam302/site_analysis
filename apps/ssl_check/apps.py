from django.apps import AppConfig


class SSLCheckConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ssl_check"
    verbose_name = "SSL/TLS Checks"

    def ready(self) -> None:
        from apps.ssl_check import signals  # noqa: F401
