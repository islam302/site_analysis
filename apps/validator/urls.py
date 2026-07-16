"""Validator routes, mounted at /api/v1/ (see apps.api_v1.urls).

Two prefixes live here:
- ``validate/``           POST — submit a URL for validation
- ``validations/``        GET  — list jobs; ``{id}/`` detail; ``{id}/schemas/``
                                 and ``{id}/issues/`` sub-resources
"""
from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.validator.views import SubmitValidationView, ValidationViewSet

app_name = "validator"

router = SimpleRouter(trailing_slash=True)
router.register("validations", ValidationViewSet, basename="validation")

urlpatterns = [
    path("validate/", SubmitValidationView.as_view(), name="validate"),
    *router.urls,
]
