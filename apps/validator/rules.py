"""Declarative Schema.org validation rules.

Every supported type is described purely as data here — required/recommended
properties, expected value types, nested-list rules, and the fields Google needs
for a rich result. The validator (:mod:`schema_validator_service`) is a generic
engine driven entirely by these declarations, so adding a new type means adding
one entry to :data:`RULES` — no changes to the validation logic.

Expected-type tokens understood by the engine:
    text            a string
    url             a URL string
    number          an int/float or numeric string (e.g. a price)
    date            an ISO date string (YYYY-MM-DD...)
    datetime        an ISO date/time string
    image           a URL string, an ImageObject dict, or a list of either
    object          a dict (or list of dicts)
    array           a list
    text_or_object  a string OR a dict/list (properties that accept either form)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SchemaRule:
    """Validation rules for one Schema.org type."""

    # Missing => error.
    required: tuple[str, ...] = ()
    # Missing => warning.
    recommended: tuple[str, ...] = ()
    # property name -> expected type token (wrong type => error).
    property_types: dict[str, str] = field(default_factory=dict)
    # Fields Google needs for this type's rich result.
    rich_result_required: tuple[str, ...] = ()

    # For list-valued types (BreadcrumbList, FAQPage): the property holding the
    # list, the expected @type of each element, and each element's requirements.
    list_property: str | None = None
    list_item_type: str | None = None
    list_item_required: tuple[str, ...] = ()
    # nested requirement within each list element: subprop -> required subfields.
    list_item_nested: dict[str, tuple[str, ...]] = field(default_factory=dict)

    # For a single nested object (e.g. Product.offers): missing subfields => warning.
    object_recommended: dict[str, tuple[str, ...]] = field(default_factory=dict)


# Human-readable names for the expected-type tokens (used in issue messages).
TYPE_LABELS = {
    "text": "text",
    "url": "a valid URL",
    "number": "numeric",
    "date": "a date (YYYY-MM-DD)",
    "datetime": "a date/time (ISO 8601)",
    "image": "a URL or ImageObject",
    "object": "an object",
    "array": "an array",
    "text_or_object": "text or an object",
}


RULES: dict[str, SchemaRule] = {}


def _register(types: tuple[str, ...], rule: SchemaRule) -> None:
    """Register the same rule under one or more type names (case-sensitive)."""
    for name in types:
        RULES[name] = rule


def get_rule(schema_type: str | None) -> SchemaRule | None:
    """Return the rule for ``schema_type`` (matched case-insensitively)."""
    if not schema_type:
        return None
    if schema_type in RULES:
        return RULES[schema_type]
    lowered = schema_type.lower()
    for name, rule in RULES.items():
        if name.lower() == lowered:
            return rule
    return None


def supported_types() -> list[str]:
    return sorted(RULES.keys())


# --------------------------------------------------------------------------- #
# The registry                                                                #
# --------------------------------------------------------------------------- #
_register(
    ("Organization",),
    SchemaRule(
        required=("name", "url"),
        recommended=("logo", "contactPoint"),
        property_types={"url": "url", "logo": "image"},
        rich_result_required=("name", "url", "logo"),
    ),
)

_register(
    ("Product",),
    SchemaRule(
        required=("name", "image"),
        recommended=("offers", "description", "brand"),
        property_types={"image": "image", "offers": "object"},
        object_recommended={"offers": ("price", "priceCurrency", "availability")},
        rich_result_required=("name", "image", "offers"),
    ),
)

_register(
    ("Article", "NewsArticle", "BlogPosting"),
    SchemaRule(
        required=("headline", "author", "datePublished", "image"),
        recommended=("publisher", "dateModified"),
        property_types={
            "headline": "text",
            "datePublished": "datetime",
            "image": "image",
            "author": "text_or_object",
        },
        rich_result_required=("headline", "image", "datePublished", "author"),
    ),
)

_register(
    ("BreadcrumbList",),
    SchemaRule(
        required=("itemListElement",),
        property_types={"itemListElement": "array"},
        list_property="itemListElement",
        list_item_required=("position", "name", "item"),
        rich_result_required=("itemListElement",),
    ),
)

_register(
    ("FAQPage",),
    SchemaRule(
        required=("mainEntity",),
        property_types={"mainEntity": "array"},
        list_property="mainEntity",
        list_item_type="Question",
        list_item_required=("name", "acceptedAnswer"),
        list_item_nested={"acceptedAnswer": ("text",)},
        rich_result_required=("mainEntity",),
    ),
)

_register(
    ("LocalBusiness",),
    SchemaRule(
        required=("name", "address", "telephone"),
        recommended=("openingHours", "priceRange", "geo"),
        property_types={"address": "text_or_object", "telephone": "text"},
        rich_result_required=("name", "address", "telephone"),
    ),
)

_register(
    ("Event",),
    SchemaRule(
        required=("name", "startDate", "location"),
        recommended=("endDate", "offers", "description"),
        property_types={"startDate": "datetime", "location": "text_or_object"},
        rich_result_required=("name", "startDate", "location"),
    ),
)

_register(
    ("Review",),
    SchemaRule(
        required=("itemReviewed", "reviewRating", "author"),
        recommended=("reviewBody", "datePublished"),
        property_types={"reviewRating": "object", "author": "text_or_object"},
        object_recommended={"reviewRating": ("ratingValue",)},
        rich_result_required=("itemReviewed", "reviewRating", "author"),
    ),
)
