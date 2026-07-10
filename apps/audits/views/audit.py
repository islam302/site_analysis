"""Accessibility audit views.

All endpoints require authentication (audits are credit-scoped to a user).
``run`` is synchronous — WAVE returns the full report in one call — and is
throttled to 10/min per user on top of credit-based limiting.
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

from apps.audits.filters import AuditFilter
from apps.audits.models import AccessibilityAudit
from apps.audits.selectors import get_audit_issues, get_user_audits
from apps.audits.serializers import (
    AuditIssueSerializer,
    AuditListSerializer,
    AuditSerializer,
    RunAuditInputSerializer,
)
from apps.audits.services import run_accessibility_audit
from apps.audits.throttling import AuditRateThrottle
from apps.common.pagination import DefaultPagination, get_paginated_response

logger = logging.getLogger("apps.audits")


class RunAuditView(APIView):
    """POST /audits/run/ — run a WAVE accessibility audit.

    Public: authenticated users are credit-gated (1 credit); anonymous users run
    without credits.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuditRateThrottle]

    @extend_schema(
        request=RunAuditInputSerializer,
        responses={201: AuditSerializer},
        summary="Run an accessibility audit",
    )
    def post(self, request: Request) -> Response:
        serializer = RunAuditInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        audit = run_accessibility_audit(user=request.user, **serializer.validated_data)

        return Response(AuditSerializer(audit).data, status=status.HTTP_201_CREATED)


class AuditViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """List / retrieve / soft-delete accessibility audits.

    Detail (retrieve) is public by UUID so anonymous submitters can fetch their
    audit; list/delete are scoped to the authenticated owner.
    """

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = AuditFilter
    ordering_fields = ["created_at", "total_errors", "total_contrast_errors"]
    ordering = ["-created_at"]
    queryset = AccessibilityAudit.objects.none()

    def get_queryset(self):
        if self.action == "retrieve":
            return AccessibilityAudit.objects.prefetch_related("issues").all()
        user = self.request.user
        if not user.is_authenticated:
            return AccessibilityAudit.objects.none()
        return get_user_audits(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return AuditListSerializer
        return AuditSerializer

    def perform_destroy(self, instance: AccessibilityAudit) -> None:
        instance.soft_delete()
        logger.info("Audit soft-deleted", extra={"audit_id": str(instance.id)})


class AuditIssuesView(APIView):
    """GET /audits/{id}/issues/ — issues for one audit (filter by issue_type)."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: AuditIssueSerializer(many=True)},
        summary="List issues for an audit",
    )
    def get(self, request: Request, pk: str) -> Response:
        issues = get_audit_issues(
            audit_id=pk,
            issue_type=request.query_params.get("issue_type"),
        )
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=AuditIssueSerializer,
            queryset=issues,
            request=request,
            view=self,
        )
