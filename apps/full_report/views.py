"""Combined full-report views (async via Celery).

POST creates a job and returns immediately with a ``status_url``; the Celery
task builds the PDF in the background. GET polls the job for its status and,
once completed, a ``download_url``.
"""
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.throttling import AnalysisBurstThrottle, AnalysisDailyThrottle
from apps.full_report.models import FullReport
from apps.full_report.serializers import FullReportInputSerializer, FullReportSerializer

logger = logging.getLogger("apps.full_report")


class FullReportCreateView(APIView):
    """POST /full_report/ — queue a combined report; returns a job + status URL."""

    permission_classes = [AllowAny]
    throttle_classes = [AnalysisBurstThrottle, AnalysisDailyThrottle]

    @extend_schema(
        request=FullReportInputSerializer,
        responses={202: OpenApiResponse(description="Job queued: id, status, status_url")},
        summary="Queue a combined PDF report (async)",
    )
    def post(self, request: Request) -> Response:
        serializer = FullReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report = FullReport.objects.create(
            user=request.user if request.user.is_authenticated else None,
            url=data["url"],
            strategy=data["strategy"],
            lang=data["lang"],
        )

        # Import here to avoid a circular import at module load.
        from apps.full_report.tasks import run_full_report_task

        transaction.on_commit(lambda: run_full_report_task.delay(report_id=str(report.id)))

        status_url = request.build_absolute_uri(
            reverse("full_report:detail", args=[report.id])
        )
        logger.info("Full report queued", extra={"report_id": str(report.id)})
        return Response(
            {"id": str(report.id), "status": report.status, "status_url": status_url},
            status=status.HTTP_202_ACCEPTED,
        )


class FullReportDetailView(APIView):
    """GET /full_report/{id}/ — poll job status; download_url appears when ready."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: FullReportSerializer}, summary="Get report job status")
    def get(self, request: Request, pk: str) -> Response:
        report = get_object_or_404(FullReport, id=pk)
        return Response(
            FullReportSerializer(report, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
