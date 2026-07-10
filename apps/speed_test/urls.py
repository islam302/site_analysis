"""Combined speed test routes, mounted under /api/v1/speed_test/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.speed_test.views import SpeedTestAnalyzeView, SpeedTestViewSet

app_name = "speed_test"

router = DefaultRouter()
router.register("reports", SpeedTestViewSet, basename="report")

urlpatterns = [
    path("analyze/", SpeedTestAnalyzeView.as_view(), name="analyze"),
    path("", include(router.urls)),
]
