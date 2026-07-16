"""Validate a single structured-data object against the Schema.org rule registry.

A generic engine: it reads the declarative rule for the item's ``@type`` from
:mod:`apps.validator.rules` and emits issues (error/warning/info). It never
hard-codes per-type logic, so new types are added by editing the registry only.
"""
from __future__ import annotations

import re

from apps.validator.constants import PARSE_ERROR_KEY, UNKNOWN_TYPE, IssueSeverity
from apps.validator.rules import TYPE_LABELS, SchemaRule, get_rule

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _issue(severity: str, field: str, message: str, suggestion: str | None = None) -> dict:
    return {"severity": severity, "field": field, "message": message, "suggestion": suggestion}


def _result(schema_type: str, is_valid: bool, rich: bool, issues: list[dict]) -> dict:
    return {
        "schema_type": schema_type,
        "is_valid": is_valid,
        "google_rich_result_eligible": rich,
        "issues": issues,
    }


def resolve_type(data: dict) -> str | None:
    """Return the short Schema.org type name from a structured-data object."""
    if not isinstance(data, dict) or PARSE_ERROR_KEY in data:
        return None
    value = data.get("@type")
    if isinstance(value, list):
        value = next((v for v in value if v), None)
    if isinstance(value, str) and value.strip():
        return value.strip().rstrip("/").split("/")[-1].split("#")[-1]
    return None


def _is_missing(data: dict, prop: str) -> bool:
    """True when a property is absent or effectively empty."""
    if prop not in data:
        return True
    value = data[prop]
    if value is None:
        return False if isinstance(value, (int, float)) else True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _looks_like_url(value) -> bool:
    return isinstance(value, str) and value.strip().lower().startswith(
        ("http://", "https://", "//", "/")
    )


def _is_numeric(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", ""))
            return True
        except ValueError:
            return False
    return False


def _type_ok(value, expected: str) -> bool:
    """Return True if ``value`` satisfies the ``expected`` type token."""
    if expected == "text":
        return isinstance(value, str) or (
            isinstance(value, list) and all(isinstance(v, str) for v in value)
        )
    if expected == "url":
        return _looks_like_url(value)
    if expected == "number":
        return _is_numeric(value)
    if expected in ("date", "datetime"):
        return isinstance(value, str) and bool(_ISO_DATE.match(value.strip()))
    if expected == "image":
        if _looks_like_url(value) or isinstance(value, dict):
            return True
        return isinstance(value, list) and all(
            _looks_like_url(v) or isinstance(v, dict) for v in value
        )
    if expected == "object":
        return isinstance(value, dict) or (
            isinstance(value, list) and all(isinstance(v, dict) for v in value)
        )
    if expected == "array":
        return isinstance(value, list)
    if expected == "text_or_object":
        return isinstance(value, (str, dict, list))
    return True


def _validate_list(rule: SchemaRule, schema_type: str, data: dict) -> list[dict]:
    """Validate the elements of a list-valued property (Breadcrumb/FAQ style)."""
    issues: list[dict] = []
    prop = rule.list_property
    value = data.get(prop)
    if not isinstance(value, list):
        return issues  # missing/wrong-type already reported by the caller

    for index, entry in enumerate(value):
        loc = f"{prop}[{index}]"
        if not isinstance(entry, dict):
            issues.append(
                _issue(IssueSeverity.ERROR, loc, f"{loc} must be an object.", None)
            )
            continue
        if rule.list_item_type:
            entry_type = resolve_type(entry)
            if entry_type and entry_type != rule.list_item_type:
                issues.append(
                    _issue(
                        IssueSeverity.WARNING,
                        f"{loc}.@type",
                        f'{loc} should be of type "{rule.list_item_type}", got "{entry_type}".',
                        f'Set "@type": "{rule.list_item_type}" on each list item.',
                    )
                )
        for req in rule.list_item_required:
            if _is_missing(entry, req):
                issues.append(
                    _issue(
                        IssueSeverity.ERROR,
                        f"{loc}.{req}",
                        f'{loc} is missing required property "{req}".',
                        f'Add "{req}" to each "{prop}" entry.',
                    )
                )
        for parent, subfields in rule.list_item_nested.items():
            child = entry.get(parent)
            if isinstance(child, dict):
                for sub in subfields:
                    if _is_missing(child, sub):
                        issues.append(
                            _issue(
                                IssueSeverity.ERROR,
                                f"{loc}.{parent}.{sub}",
                                f'{loc}.{parent} is missing required property "{sub}".',
                                f'Add "{sub}" inside "{parent}".',
                            )
                        )
    return issues


def _validate_object_recommended(rule: SchemaRule, data: dict) -> list[dict]:
    """Warn on missing sub-properties of a nested object (e.g. offers.price)."""
    issues: list[dict] = []
    for parent, subfields in rule.object_recommended.items():
        obj = data.get(parent)
        candidates = obj if isinstance(obj, list) else [obj]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for sub in subfields:
                if _is_missing(candidate, sub):
                    issues.append(
                        _issue(
                            IssueSeverity.WARNING,
                            f"{parent}.{sub}",
                            f'Recommended property "{parent}.{sub}" is missing.',
                            f'Add "{sub}" inside "{parent}" for richer results.',
                        )
                    )
    return issues


def _rich_result_eligible(rule: SchemaRule, data: dict) -> bool:
    return all(not _is_missing(data, prop) for prop in rule.rich_result_required)


def validate_schema(*, schema_type: str | None, data: dict) -> dict:
    """Validate one structured-data object.

    Returns a dict with ``schema_type``, ``is_valid``,
    ``google_rich_result_eligible`` and ``issues`` (a list of
    ``{severity, field, message, suggestion}``).
    """
    # A JSON-LD block that failed to parse.
    if isinstance(data, dict) and PARSE_ERROR_KEY in data:
        return _result(
            UNKNOWN_TYPE,
            False,
            False,
            [
                _issue(
                    IssueSeverity.ERROR,
                    "@type",
                    f"Invalid JSON-LD syntax: {data[PARSE_ERROR_KEY]}",
                    "Fix the JSON so it parses (check quotes, commas and brackets).",
                )
            ],
        )

    if not schema_type:
        return _result(
            UNKNOWN_TYPE,
            False,
            False,
            [
                _issue(
                    IssueSeverity.ERROR,
                    "@type",
                    "Missing @type — the structured-data object has no Schema.org type.",
                    'Add an "@type", e.g. "@type": "Product".',
                )
            ],
        )

    rule = get_rule(schema_type)
    if rule is None:
        # A real Schema.org type may exist that we have no rules for; don't fail it.
        return _result(
            schema_type,
            True,
            False,
            [
                _issue(
                    IssueSeverity.INFO,
                    "@type",
                    f'No validation rules defined for type "{schema_type}".',
                    None,
                )
            ],
        )

    issues: list[dict] = []

    for prop in rule.required:
        if _is_missing(data, prop):
            issues.append(
                _issue(
                    IssueSeverity.ERROR,
                    prop,
                    f'Missing required property "{prop}" for {schema_type}.',
                    f'Add the "{prop}" property to your {schema_type} schema.',
                )
            )

    for prop in rule.recommended:
        if _is_missing(data, prop):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    prop,
                    f'Recommended property "{prop}" is missing for {schema_type}.',
                    f'Add "{prop}" to improve SEO and rich-result eligibility.',
                )
            )

    for prop, expected in rule.property_types.items():
        if not _is_missing(data, prop) and not _type_ok(data[prop], expected):
            issues.append(
                _issue(
                    IssueSeverity.ERROR,
                    prop,
                    f'Property "{prop}" should be {TYPE_LABELS.get(expected, expected)}.',
                    f'Provide "{prop}" as {TYPE_LABELS.get(expected, expected)}.',
                )
            )

    if rule.list_property:
        issues.extend(_validate_list(rule, schema_type, data))
    issues.extend(_validate_object_recommended(rule, data))

    has_error = any(i["severity"] == IssueSeverity.ERROR for i in issues)
    is_valid = not has_error
    rich = is_valid and _rich_result_eligible(rule, data)
    return _result(schema_type, is_valid, rich, issues)
