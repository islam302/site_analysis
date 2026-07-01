"""Analysis routes, mounted under /api/v1/analysis/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.analysis.views import (
    AnalysisHistoryView,
    AnalysisReportViewSet,
    AnalyzeView,
)

app_name = "analysis"

router = DefaultRouter()
router.register("reports", AnalysisReportViewSet, basename="report")

urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="analyze"),
    path("history/", AnalysisHistoryView.as_view(), name="history"),
    path("", include(router.urls)),
]
