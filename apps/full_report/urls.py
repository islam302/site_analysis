"""Full report routes, mounted under /api/v1/full_report/."""
from django.urls import path

from apps.full_report.views import FullReportCreateView, FullReportDetailView

app_name = "full_report"

urlpatterns = [
    path("", FullReportCreateView.as_view(), name="run"),
    path("<uuid:pk>/", FullReportDetailView.as_view(), name="detail"),
]
