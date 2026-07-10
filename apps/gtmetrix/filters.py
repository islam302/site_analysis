"""django-filter FilterSet for the GTmetrix reports list endpoint."""
import django_filters as filters

from apps.gtmetrix.constants import ReportStatus
from apps.gtmetrix.models import GTmetrixReport


class GTmetrixReportFilter(filters.FilterSet):
    url = filters.CharFilter(lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=ReportStatus.choices)
    grade = filters.CharFilter(field_name="gtmetrix_grade", lookup_expr="iexact")

    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    min_performance = filters.NumberFilter(field_name="performance_score", lookup_expr="gte")
    max_performance = filters.NumberFilter(field_name="performance_score", lookup_expr="lte")
    min_structure = filters.NumberFilter(field_name="structure_score", lookup_expr="gte")

    class Meta:
        model = GTmetrixReport
        fields = ["url", "status"]
