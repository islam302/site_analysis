"""Validator views: submit a URL and read your jobs, schemas and issues.

All endpoints require authentication and are scoped to the requesting user via
the selectors — a user can only ever see their own validation jobs.
"""
import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import DefaultPagination, get_paginated_response
from apps.validator.filters import SchemaIssueFilter, SchemaItemFilter
from apps.validator.models import ValidationJob
from apps.validator.selectors import (
    get_issues,
    get_job_detail,
    get_jobs,
    get_schemas,
)
from apps.validator.serializers import (
    SchemaIssueSerializer,
    SchemaItemSerializer,
    SubmitValidationSerializer,
    ValidationJobListSerializer,
    ValidationJobSerializer,
)
from apps.validator.services import submit_validation
from apps.validator.throttling import ValidationBurstThrottle, ValidationDailyThrottle

logger = logging.getLogger("apps.validator")


class SubmitValidationView(APIView):
    """POST /validate/ — queue structured-data validation for a URL."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ValidationBurstThrottle, ValidationDailyThrottle]

    @extend_schema(
        request=SubmitValidationSerializer,
        responses={202: ValidationJobSerializer},
        summary="Submit a URL for structured-data validation",
    )
    def post(self, request: Request) -> Response:
        serializer = SubmitValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = submit_validation(user=request.user, url=serializer.validated_data["url"])
        return Response(
            ValidationJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ValidationViewSet(viewsets.GenericViewSet):
    """Read validation jobs and their schemas/issues (owner-only)."""

    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = ValidationJobSerializer
    # Declared for schema generation; real rows come from the user-scoped selectors.
    queryset = ValidationJob.objects.none()

    @extend_schema(responses={200: ValidationJobListSerializer}, summary="List your validation jobs")
    def list(self, request: Request) -> Response:
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=ValidationJobListSerializer,
            queryset=get_jobs(user=request.user),
            request=request,
            view=self,
        )

    @extend_schema(
        responses={200: ValidationJobSerializer},
        summary="Get a job with all schemas and issues",
    )
    def retrieve(self, request: Request, pk: str) -> Response:
        job = get_job_detail(user=request.user, job_id=pk)
        return Response(
            ValidationJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: SchemaItemSerializer},
        summary="List schemas found (filter by type, format, is_valid)",
    )
    @action(detail=True, methods=["get"])
    def schemas(self, request: Request, pk: str) -> Response:
        results = SchemaItemFilter(
            request.query_params, queryset=get_schemas(user=request.user, job_id=pk)
        ).qs
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=SchemaItemSerializer,
            queryset=results,
            request=request,
            view=self,
        )

    @extend_schema(
        responses={200: SchemaIssueSerializer},
        summary="List all issues (filter by severity)",
    )
    @action(detail=True, methods=["get"])
    def issues(self, request: Request, pk: str) -> Response:
        results = SchemaIssueFilter(
            request.query_params, queryset=get_issues(user=request.user, job_id=pk)
        ).qs
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=SchemaIssueSerializer,
            queryset=results,
            request=request,
            view=self,
        )
