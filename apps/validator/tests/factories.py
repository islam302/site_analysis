"""Factories for validator tests."""
import factory

from apps.users.tests.factories import UserFactory
from apps.validator.constants import IssueSeverity, SchemaFormat, ValidationStatus
from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob


class ValidationJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ValidationJob

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.test/")
    status = ValidationStatus.COMPLETED


class SchemaItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchemaItem

    job = factory.SubFactory(ValidationJobFactory)
    schema_type = "Product"
    format = SchemaFormat.JSON_LD
    raw_data = factory.LazyFunction(lambda: {"@type": "Product", "name": "X"})
    is_valid = True
    google_rich_result_eligible = False


class SchemaIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchemaIssue

    schema_item = factory.SubFactory(SchemaItemFactory)
    severity = IssueSeverity.ERROR
    field = "image"
    message = "Missing required property \"image\"."
    suggestion = "Add image."
