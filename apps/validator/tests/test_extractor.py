"""Unit tests for the structured-data extractors (no DB, no network)."""
from apps.validator.constants import PARSE_ERROR_KEY
from apps.validator.services.extractor_service import (
    extract_json_ld,
    extract_microdata,
    extract_rdfa,
)
from apps.validator.tests import fixtures as fx


class TestJsonLd:
    def test_single_object(self):
        items = extract_json_ld(html_content=fx.ORG_VALID)
        assert len(items) == 1
        assert items[0]["@type"] == "Organization"
        assert items[0]["name"] == "Acme Corp"

    def test_array_in_one_script(self):
        items = extract_json_ld(html_content=fx.JSON_LD_ARRAY)
        assert len(items) == 2
        assert {i["name"] for i in items} == {"A", "B"}

    def test_graph_is_flattened(self):
        items = extract_json_ld(html_content=fx.GRAPH_MULTIPLE)
        types = {i.get("@type") for i in items}
        assert types == {"Organization", "WebSite"}

    def test_malformed_json_becomes_marker(self):
        items = extract_json_ld(html_content=fx.MALFORMED_JSON_LD)
        assert len(items) == 1
        assert PARSE_ERROR_KEY in items[0]

    def test_no_structured_data(self):
        assert extract_json_ld(html_content=fx.NO_STRUCTURED_DATA) == []


class TestMicrodata:
    def test_product_with_nested_offer(self):
        items = extract_microdata(html_content=fx.MICRODATA_PRODUCT)
        assert len(items) == 1
        product = items[0]
        assert product["@type"] == "Product"
        assert product["name"] == "Micro Widget"
        assert product["image"] == "https://m.example/w.jpg"
        # Nested Offer parsed as a child object, not merged into the parent.
        assert isinstance(product["offers"], dict)
        assert product["offers"]["@type"] == "Offer"
        assert product["offers"]["price"] == "19.99"
        assert product["offers"]["priceCurrency"] == "USD"

    def test_no_microdata(self):
        assert extract_microdata(html_content=fx.ORG_VALID) == []


class TestRdfa:
    def test_localbusiness(self):
        items = extract_rdfa(html_content=fx.RDFA_LOCALBUSINESS)
        assert len(items) == 1
        biz = items[0]
        assert biz["@type"] == "LocalBusiness"
        assert biz["name"] == "Corner Cafe"
        assert biz["address"] == "123 Main St"
        assert "telephone" not in biz

    def test_no_rdfa(self):
        assert extract_rdfa(html_content=fx.ORG_VALID) == []
