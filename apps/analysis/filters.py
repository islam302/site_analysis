"""django-filter FilterSet for the reports list endpoint."""
import django_filters as filters

from apps.analysis.constants import ReportStatus, Strategy
from apps.analysis.models import AnalysisReport


class AnalysisReportFilter(filters.FilterSet):
    url = filters.CharFilter(lookup_expr="icontains")
    strategy = filters.ChoiceFilter(choices=Strategy.choices)
    status = filters.ChoiceFilter(choices=ReportStatus.choices)

    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    min_performance = filters.NumberFilter(field_name="performance_score", lookup_expr="gte")
    max_performance = filters.NumberFilter(field_name="performance_score", lookup_expr="lte")
    min_seo = filters.NumberFilter(field_name="seo_score", lookup_expr="gte")
    max_seo = filters.NumberFilter(field_name="seo_score", lookup_expr="lte")
    min_accessibility = filters.NumberFilter(field_name="accessibility_score", lookup_expr="gte")
    min_best_practices = filters.NumberFilter(field_name="best_practices_score", lookup_expr="gte")

    class Meta:
        model = AnalysisReport
        fields = ["url", "strategy", "status"]
