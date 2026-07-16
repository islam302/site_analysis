"""django-filter FilterSets for schema items and issues."""
import django_filters as filters

from apps.validator.constants import IssueSeverity, SchemaFormat
from apps.validator.models import SchemaIssue, SchemaItem


class SchemaItemFilter(filters.FilterSet):
    schema_type = filters.CharFilter(field_name="schema_type", lookup_expr="iexact")
    format = filters.ChoiceFilter(choices=SchemaFormat.choices)
    is_valid = filters.BooleanFilter()

    class Meta:
        model = SchemaItem
        fields = ["schema_type", "format", "is_valid"]


class SchemaIssueFilter(filters.FilterSet):
    severity = filters.ChoiceFilter(choices=IssueSeverity.choices)

    class Meta:
        model = SchemaIssue
        fields = ["severity"]
