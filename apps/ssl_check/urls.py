"""SSL check routes, mounted under /api/v1/ssl/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.ssl_check.views import SSLAnalyzeView, SSLReportViewSet

app_name = "ssl_check"

router = DefaultRouter()
router.register("reports", SSLReportViewSet, basename="report")

urlpatterns = [
    path("analyze/", SSLAnalyzeView.as_view(), name="analyze"),
    path("", include(router.urls)),
]
