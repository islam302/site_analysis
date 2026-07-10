"""django-filter FilterSets for the audits endpoints."""
import django_filters as filters

from apps.audits.constants import AuditStatus, IssueType
from apps.audits.models import AccessibilityAudit, AuditIssue


class AuditFilter(filters.FilterSet):
    url = filters.CharFilter(lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=AuditStatus.choices)
    wcag_level = filters.CharFilter(lookup_expr="iexact")

    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    min_errors = filters.NumberFilter(field_name="total_errors", lookup_expr="gte")
    max_errors = filters.NumberFilter(field_name="total_errors", lookup_expr="lte")

    class Meta:
        model = AccessibilityAudit
        fields = ["url", "status", "wcag_level"]


class AuditIssueFilter(filters.FilterSet):
    issue_type = filters.ChoiceFilter(choices=IssueType.choices)
    wave_id = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = AuditIssue
        fields = ["issue_type", "wave_id"]
