"""GTmetrix routes, mounted under /api/v1/gtmetrix/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.gtmetrix.views import GTmetrixAnalyzeView, GTmetrixReportViewSet

app_name = "gtmetrix"

router = DefaultRouter()
router.register("reports", GTmetrixReportViewSet, basename="report")

urlpatterns = [
    path("analyze/", GTmetrixAnalyzeView.as_view(), name="analyze"),
    path("", include(router.urls)),
]
