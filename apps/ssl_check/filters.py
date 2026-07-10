"""django-filter FilterSet for the SSL reports list endpoint."""
import django_filters as filters

from apps.ssl_check.constants import ReportStatus
from apps.ssl_check.models import SSLReport


class SSLReportFilter(filters.FilterSet):
    host = filters.CharFilter(lookup_expr="icontains")
    url = filters.CharFilter(lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=ReportStatus.choices)
    grade = filters.CharFilter(lookup_expr="iexact")
    has_warnings = filters.BooleanFilter()

    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = SSLReport
        fields = ["host", "url", "status", "grade", "has_warnings"]
