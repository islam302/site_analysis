from django.apps import AppConfig


class FullReportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.full_report"
    verbose_name = "Full Report (combined + PDF)"
