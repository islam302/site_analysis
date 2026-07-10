"""Thin analysis views.

Each view validates input, calls a service/selector, and returns a serialized
response. Submission endpoints (analyze, compare) carry per-user burst + daily
throttles. Reports use a GenericViewSet for list/retrieve/soft-delete.
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

from apps.analysis.filters import AnalysisReportFilter
from apps.analysis.models import AnalysisReport
from apps.analysis.selectors import get_analysis_history, get_user_reports
from apps.analysis.serializers import (
    AnalysisHistorySerializer,
    AnalysisReportListSerializer,
    AnalysisReportSerializer,
    AnalyzeInputSerializer,
)
from apps.analysis.services import submit_analysis
from apps.analysis.throttling import AnalysisBurstThrottle, AnalysisDailyThrottle
from apps.common.pagination import DefaultPagination, get_paginated_response

logger = logging.getLogger("apps.analysis")


class AnalyzeView(APIView):
    """POST /analysis/analyze/ — submit a URL for async PageSpeed analysis."""

    permission_classes = [AllowAny]  # Allow anonymous users to submit URLs for analysis.
    throttle_classes = [AnalysisBurstThrottle, AnalysisDailyThrottle]

    @extend_schema(
        request=AnalyzeInputSerializer,
        responses={202: AnalysisReportSerializer},
        summary="Submit a URL for analysis",
    )
    def post(self, request: Request) -> Response:
        serializer = AnalyzeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = submit_analysis(user=request.user, **serializer.validated_data)

        # In eager mode the task has already run on commit; reflect any updated
        # scores in the response (in async mode this is still the pending state).
        report.refresh_from_db()

        return Response(
            AnalysisReportSerializer(report).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AnalysisHistoryView(APIView):
    """GET /analysis/history/ — unique analyzed URLs with counts (cached 5 min)."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: AnalysisHistorySerializer(many=True)},
        summary="List analysis history",
    )
    def get(self, request: Request) -> Response:
        history = get_analysis_history(user=request.user) if request.user.is_authenticated else []
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=AnalysisHistorySerializer,
            queryset=history,
            request=request,
            view=self,
        )


class AnalysisReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List / retrieve / soft-delete the authenticated user's reports."""

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = AnalysisReportFilter
    ordering_fields = [
        "created_at",
        "performance_score",
        "accessibility_score",
        "best_practices_score",
        "seo_score",
    ]
    ordering = ["-created_at"]
    # Declared for schema generation; real rows come from get_queryset.
    queryset = AnalysisReport.objects.none()

    def get_queryset(self):
        # Detail (retrieve) is public by UUID so anonymous submitters can poll
        # their report; list/delete stay scoped to the authenticated owner.
        if self.action == "retrieve":
            return AnalysisReport.objects.all()
        user = self.request.user
        if not user.is_authenticated:
            return AnalysisReport.objects.none()
        return get_user_reports(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return AnalysisReportListSerializer
        return AnalysisReportSerializer

    def perform_destroy(self, instance: AnalysisReport) -> None:
        instance.soft_delete()
        logger.info("Report soft-deleted", extra={"report_id": str(instance.id)})
