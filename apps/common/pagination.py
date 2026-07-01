"""Custom pagination classes and a helper for ViewSet-style paginated responses."""
from collections.abc import Iterable

from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView


class DefaultPagination(PageNumberPagination):
    """Standard page-number pagination used across the API."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LargeResultsPagination(PageNumberPagination):
    """For endpoints that legitimately return large collections."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


def get_paginated_response(
    *,
    pagination_class: type[PageNumberPagination],
    serializer_class: type[Serializer],
    queryset: Iterable,
    request: Request,
    view: APIView,
) -> Response:
    """Paginate ``queryset`` and serialize it, returning a DRF ``Response``.

    Lets ``ViewSet`` ``list`` methods reuse DRF pagination without subclassing
    ``GenericViewSet``.
    """
    paginator = pagination_class()
    page = paginator.paginate_queryset(queryset, request, view=view)
    if page is not None:
        serializer = serializer_class(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True, context={"request": request})
    return Response(serializer.data)
