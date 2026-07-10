"""Combined speed test views (Google PageSpeed + GTmetrix).

Requires authentication because it triggers the paid GTmetrix API.
"""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.throttling import AnalysisBurstThrottle, AnalysisDailyThrottle
from apps.common.pagination import DefaultPagination
from apps.speed_test.models import SpeedTest
from apps.speed_test.selectors import get_user_speed_tests
from apps.speed_test.serializers import (
    SpeedTestInputSerializer,
    SpeedTestListSerializer,
    SpeedTestSerializer,
)
from apps.speed_test.services import submit_speed_test

logger = logging.getLogger("apps.speed_test")


class SpeedTestAnalyzeView(APIView):
    """POST /speed_test/analyze/ — run Google PageSpeed + GTmetrix together."""

    permission_classes = [AllowAny]
    throttle_classes = [AnalysisBurstThrottle, AnalysisDailyThrottle]

    @extend_schema(
        request=SpeedTestInputSerializer,
        responses={202: SpeedTestSerializer},
        summary="Run a combined speed test (PageSpeed + GTmetrix)",
    )
    def post(self, request: Request) -> Response:
        serializer = SpeedTestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        speed_test = submit_speed_test(user=request.user, **serializer.validated_data)

        # Reflect any eager-mode updates on the two sub-reports.
        if speed_test.google_report_id:
            speed_test.google_report.refresh_from_db()
        if speed_test.gtmetrix_report_id:
            speed_test.gtmetrix_report.refresh_from_db()

        return Response(
            SpeedTestSerializer(speed_test).data,
            status=status.HTTP_202_ACCEPTED,
        )


class SpeedTestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List / retrieve / soft-delete the authenticated user's speed tests."""

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["strategy", "url"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    queryset = SpeedTest.objects.none()

    def get_queryset(self):
        # Detail is public by UUID (anonymous submitters poll their result);
        # list/delete stay scoped to the authenticated owner.
        if self.action == "retrieve":
            return SpeedTest.objects.select_related("google_report", "gtmetrix_report").all()
        user = self.request.user
        if not user.is_authenticated:
            return SpeedTest.objects.none()
        return get_user_speed_tests(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return SpeedTestListSerializer
        return SpeedTestSerializer

    def perform_destroy(self, instance: SpeedTest) -> None:
        instance.soft_delete()
        logger.info("Speed test soft-deleted", extra={"speed_test_id": str(instance.id)})
