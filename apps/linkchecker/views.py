"""Link-checker views: submit a crawl and read its jobs / link results."""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import DefaultPagination, get_paginated_response
from apps.linkchecker.constants import StatusCategory
from apps.linkchecker.filters import LinkResultFilter
from apps.linkchecker.models import CrawlJob
from apps.linkchecker.selectors import get_crawl_detail, get_crawl_jobs, get_link_results
from apps.linkchecker.serializers import (
    CrawlJobListSerializer,
    CrawlJobSerializer,
    CrawlProgressSerializer,
    LinkResultSerializer,
    SubmitCrawlSerializer,
)
from apps.linkchecker.services import submit_crawl
from apps.linkchecker.throttling import CrawlBurstThrottle, CrawlDailyThrottle

logger = logging.getLogger("apps.linkchecker")


class CrawlViewSet(viewsets.GenericViewSet):
    """Submit crawls and read jobs, link results, broken links, and progress."""

    permission_classes = [AllowAny]
    pagination_class = DefaultPagination
    queryset = CrawlJob.objects.none()

    def get_throttles(self):
        # Rate-limit submissions only (3/min, 20/day per IP).
        if self.action == "create":
            return [CrawlBurstThrottle(), CrawlDailyThrottle()]
        return []

    @extend_schema(request=SubmitCrawlSerializer, responses={202: CrawlJobSerializer},
                   summary="Submit a URL for link checking")
    def create(self, request: Request) -> Response:
        serializer = SubmitCrawlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = submit_crawl(**serializer.validated_data)
        return Response(CrawlJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={200: CrawlJobListSerializer}, summary="List crawl jobs")
    def list(self, request: Request) -> Response:
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=CrawlJobListSerializer,
            queryset=get_crawl_jobs(),
            request=request,
            view=self,
        )

    @extend_schema(responses={200: CrawlJobSerializer}, summary="Get a crawl job with stats")
    def retrieve(self, request: Request, pk: str) -> Response:
        job = get_crawl_detail(job_id=pk)
        return Response(CrawlJobSerializer(job).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: LinkResultSerializer}, summary="All link results for a job")
    @action(detail=True, methods=["get"])
    def links(self, request: Request, pk: str) -> Response:
        results = LinkResultFilter(
            request.query_params, queryset=get_link_results(job_id=pk)
        ).qs
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=LinkResultSerializer,
            queryset=results,
            request=request,
            view=self,
        )

    @extend_schema(responses={200: LinkResultSerializer}, summary="Broken links only")
    @action(detail=True, methods=["get"])
    def broken(self, request: Request, pk: str) -> Response:
        results = get_link_results(job_id=pk).filter(status_category=StatusCategory.BROKEN)
        return get_paginated_response(
            pagination_class=DefaultPagination,
            serializer_class=LinkResultSerializer,
            queryset=results,
            request=request,
            view=self,
        )

    @extend_schema(responses={200: CrawlProgressSerializer}, summary="Crawl progress")
    @action(detail=True, methods=["get"])
    def progress(self, request: Request, pk: str) -> Response:
        job = get_crawl_detail(job_id=pk)
        total = job.total_links_found or 0
        percent = round(job.total_checked / total * 100, 1) if total else 0.0
        data = {
            "status": job.status,
            "total_links_found": job.total_links_found,
            "total_checked": job.total_checked,
            "percent": percent,
        }
        return Response(CrawlProgressSerializer(data).data, status=status.HTTP_200_OK)
