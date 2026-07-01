"""Celery application bootstrap."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("config")

# All Celery configuration lives in Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:  # pragma: no cover - operational helper
    """Trivial task used to verify the worker is wired up correctly."""
    print(f"Request: {self.request!r}")  # noqa: T201 - intentional worker diagnostic
