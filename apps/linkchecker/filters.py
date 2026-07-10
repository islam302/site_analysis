"""django-filter FilterSet for link results."""
import django_filters as filters

from apps.linkchecker.constants import LinkType, StatusCategory
from apps.linkchecker.models import LinkResult


class LinkResultFilter(filters.FilterSet):
    status_category = filters.ChoiceFilter(choices=StatusCategory.choices)
    link_type = filters.ChoiceFilter(choices=LinkType.choices)

    class Meta:
        model = LinkResult
        fields = ["status_category", "link_type"]
