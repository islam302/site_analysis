"""Unit tests for the generic schema validation engine (no DB, no network)."""
from apps.validator.constants import IssueSeverity, PARSE_ERROR_KEY, UNKNOWN_TYPE
from apps.validator.services.schema_validator_service import resolve_type, validate_schema


def _fields(result, severity=None):
    return {
        i["field"]
        for i in result["issues"]
        if severity is None or i["severity"] == severity
    }


class TestResolveType:
    def test_plain_string(self):
        assert resolve_type({"@type": "Product"}) == "Product"

    def test_full_url(self):
        assert resolve_type({"@type": "https://schema.org/Product"}) == "Product"

    def test_list_takes_first(self):
        assert resolve_type({"@type": ["Product", "Thing"]}) == "Product"

    def test_missing_type(self):
        assert resolve_type({"name": "x"}) is None


class TestValidateSchema:
    def test_valid_organization(self):
        data = {
            "@type": "Organization",
            "name": "Acme",
            "url": "https://acme.example",
            "logo": "https://acme.example/l.png",
            "contactPoint": {"telephone": "+1"},
        }
        result = validate_schema(schema_type="Organization", data=data)
        assert result["is_valid"] is True
        assert result["google_rich_result_eligible"] is True
        assert not _fields(result, IssueSeverity.ERROR)

    def test_missing_required_is_error(self):
        result = validate_schema(schema_type="Product", data={"@type": "Product", "name": "W"})
        assert result["is_valid"] is False
        assert "image" in _fields(result, IssueSeverity.ERROR)
        assert result["google_rich_result_eligible"] is False

    def test_missing_recommended_is_warning(self):
        result = validate_schema(
            schema_type="Organization",
            data={"@type": "Organization", "name": "A", "url": "https://a.example"},
        )
        # url+name satisfy required; logo/contactPoint are recommended -> warnings.
        assert result["is_valid"] is True
        assert "logo" in _fields(result, IssueSeverity.WARNING)
        # logo is part of rich-result requirements, so not eligible.
        assert result["google_rich_result_eligible"] is False

    def test_wrong_type_is_error(self):
        data = {
            "@type": "NewsArticle",
            "headline": "H",
            "author": "Jane",
            "datePublished": "not-a-date",
            "image": "https://n.example/a.jpg",
        }
        result = validate_schema(schema_type="NewsArticle", data=data)
        assert "datePublished" in _fields(result, IssueSeverity.ERROR)

    def test_article_type_alias(self):
        # BlogPosting shares the Article rule set.
        result = validate_schema(schema_type="BlogPosting", data={"@type": "BlogPosting"})
        errors = _fields(result, IssueSeverity.ERROR)
        assert {"headline", "author", "datePublished", "image"} <= errors

    def test_breadcrumb_list_item_missing_item(self):
        data = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://x/"},
                {"@type": "ListItem", "position": 2, "name": "Blog"},
            ],
        }
        result = validate_schema(schema_type="BreadcrumbList", data=data)
        assert "itemListElement[1].item" in _fields(result, IssueSeverity.ERROR)
        assert result["is_valid"] is False

    def test_faq_missing_answer_text(self):
        data = {
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": "Q1",
                 "acceptedAnswer": {"@type": "Answer", "text": "A1"}},
                {"@type": "Question", "name": "Q2",
                 "acceptedAnswer": {"@type": "Answer"}},
            ],
        }
        result = validate_schema(schema_type="FAQPage", data=data)
        assert "mainEntity[1].acceptedAnswer.text" in _fields(result, IssueSeverity.ERROR)

    def test_product_incomplete_offer_warns(self):
        data = {
            "@type": "Product",
            "name": "G",
            "image": "https://s.example/g.jpg",
            "offers": {"@type": "Offer", "availability": "https://schema.org/InStock"},
        }
        result = validate_schema(schema_type="Product", data=data)
        warn_fields = _fields(result, IssueSeverity.WARNING)
        assert "offers.price" in warn_fields
        assert "offers.priceCurrency" in warn_fields
        # No errors -> valid, and offers present -> rich eligible.
        assert result["is_valid"] is True
        assert result["google_rich_result_eligible"] is True

    def test_missing_type_error(self):
        result = validate_schema(schema_type=None, data={"name": "x"})
        assert result["schema_type"] == UNKNOWN_TYPE
        assert result["is_valid"] is False
        assert "@type" in _fields(result, IssueSeverity.ERROR)

    def test_parse_error_marker(self):
        result = validate_schema(schema_type=None, data={PARSE_ERROR_KEY: "Expecting value"})
        assert result["is_valid"] is False
        assert any("Invalid JSON-LD" in i["message"] for i in result["issues"])

    def test_unknown_type_is_info_not_error(self):
        result = validate_schema(schema_type="WebSite", data={"@type": "WebSite", "name": "S"})
        assert result["is_valid"] is True
        assert IssueSeverity.INFO in {i["severity"] for i in result["issues"]}

    def test_local_business_missing_phone(self):
        data = {"@type": "LocalBusiness", "name": "Cafe", "address": "123 Main"}
        result = validate_schema(schema_type="LocalBusiness", data=data)
        assert "telephone" in _fields(result, IssueSeverity.ERROR)

    def test_event_and_review_required(self):
        event = validate_schema(schema_type="Event", data={"@type": "Event", "name": "E"})
        assert {"startDate", "location"} <= _fields(event, IssueSeverity.ERROR)
        review = validate_schema(schema_type="Review", data={"@type": "Review"})
        assert {"itemReviewed", "reviewRating", "author"} <= _fields(review, IssueSeverity.ERROR)
