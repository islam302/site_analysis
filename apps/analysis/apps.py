from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analysis"
    verbose_name = "PageSpeed Analysis"

    def ready(self) -> None:
        from apps.analysis import signals  # noqa: F401
