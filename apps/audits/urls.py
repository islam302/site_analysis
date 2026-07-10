"""Accessibility audit routes, mounted under /api/v1/audits/.

Explicit ``run/`` and ``{id}/issues/`` paths are declared before the router so
they resolve ahead of the viewset's ``{pk}`` detail route. ``SimpleRouter`` is
used (not ``DefaultRouter``) to avoid an API-root clash at the empty prefix.
"""
from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.audits.views import AuditIssuesView, AuditViewSet, RunAuditView

app_name = "audits"

router = SimpleRouter(trailing_slash=True)
router.register("", AuditViewSet, basename="audit")

urlpatterns = [
    path("run/", RunAuditView.as_view(), name="run"),
    path("<uuid:pk>/issues/", AuditIssuesView.as_view(), name="issues"),
    *router.urls,
]
