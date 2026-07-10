"""SSL/TLS check views: submit a scan, list/retrieve/soft-delete reports.

Public (like the other analysis tools) — sslyze is free and self-hosted, so
there's no cost to gate. Detail is public by UUID; list is owner-scoped.
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
from apps.ssl_check.filters import SSLReportFilter
from apps.ssl_check.models import SSLReport
from apps.ssl_check.selectors import get_user_ssl_reports
from apps.ssl_check.serializers import (
    SSLAnalyzeInputSerializer,
    SSLReportListSerializer,
    SSLReportSerializer,
)
from apps.ssl_check.services import submit_ssl_check

logger = logging.getLogger("apps.ssl_check")


class SSLAnalyzeView(APIView):
    """POST /ssl/analyze/ — queue an sslyze scan for a URL's host."""

    permission_classes = [AllowAny]
    throttle_classes = [AnalysisBurstThrottle, AnalysisDailyThrottle]

    @extend_schema(
        request=SSLAnalyzeInputSerializer,
        responses={202: SSLReportSerializer},
        summary="Submit a URL for an SSL/TLS scan",
    )
    def post(self, request: Request) -> Response:
        serializer = SSLAnalyzeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = submit_ssl_check(user=request.user, **serializer.validated_data)
        report.refresh_from_db()

        return Response(SSLReportSerializer(report).data, status=status.HTTP_202_ACCEPTED)


class SSLReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List / retrieve / soft-delete SSL reports."""

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SSLReportFilter
    ordering_fields = ["created_at", "cert_expires_in_days", "grade"]
    ordering = ["-created_at"]
    queryset = SSLReport.objects.none()

    def get_queryset(self):
        # Detail public by UUID; list/delete scoped to the authenticated owner.
        if self.action == "retrieve":
            return SSLReport.objects.all()
        user = self.request.user
        if not user.is_authenticated:
            return SSLReport.objects.none()
        return get_user_ssl_reports(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return SSLReportListSerializer
        return SSLReportSerializer

    def perform_destroy(self, instance: SSLReport) -> None:
        instance.soft_delete()
        logger.info("SSL report soft-deleted", extra={"report_id": str(instance.id)})
