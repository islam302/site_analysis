"""GTmetrix views: submit a test, list/retrieve/soft-delete reports.

GTmetrix consumes paid API credits, so submission requires authentication
(unlike the free Google PageSpeed endpoint).
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
from apps.gtmetrix.filters import GTmetrixReportFilter
from apps.gtmetrix.models import GTmetrixReport
from apps.gtmetrix.selectors import get_user_gtmetrix_reports
from apps.gtmetrix.serializers import (
    GTmetrixAnalyzeInputSerializer,
    GTmetrixReportListSerializer,
    GTmetrixReportSerializer,
)
from apps.gtmetrix.services import submit_gtmetrix

logger = logging.getLogger("apps.gtmetrix")


class GTmetrixAnalyzeView(APIView):
    """POST /gtmetrix/analyze/ — queue a GTmetrix test for a URL."""

    permission_classes = [AllowAny]
    throttle_classes = [AnalysisBurstThrottle, AnalysisDailyThrottle]

    @extend_schema(
        request=GTmetrixAnalyzeInputSerializer,
        responses={202: GTmetrixReportSerializer},
        summary="Submit a URL to GTmetrix",
    )
    def post(self, request: Request) -> Response:
        serializer = GTmetrixAnalyzeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = submit_gtmetrix(user=request.user, **serializer.validated_data)
        report.refresh_from_db()

        return Response(
            GTmetrixReportSerializer(report).data,
            status=status.HTTP_202_ACCEPTED,
        )


class GTmetrixReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List / retrieve / soft-delete the authenticated user's GTmetrix reports."""

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = GTmetrixReportFilter
    ordering_fields = [
        "created_at",
        "performance_score",
        "structure_score",
        "fully_loaded_time",
    ]
    ordering = ["-created_at"]
    queryset = GTmetrixReport.objects.none()

    def get_queryset(self):
        # Detail is public by UUID (anonymous submitters poll their report);
        # list/delete stay scoped to the authenticated owner.
        if self.action == "retrieve":
            return GTmetrixReport.objects.all()
        user = self.request.user
        if not user.is_authenticated:
            return GTmetrixReport.objects.none()
        return get_user_gtmetrix_reports(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return GTmetrixReportListSerializer
        return GTmetrixReportSerializer

    def perform_destroy(self, instance: GTmetrixReport) -> None:
        instance.soft_delete()
        logger.info("GTmetrix report soft-deleted", extra={"report_id": str(instance.id)})
