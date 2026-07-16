"""Integration tests for the validation service (fetch mocked, Celery eager)."""
import pytest

from apps.validator.constants import SchemaFormat, ValidationStatus
from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob
from apps.validator.services import process_validation, submit_validation
from apps.validator.tests import fixtures as fx
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _patch_fetch(mocker, html):
    return mocker.patch(
        "apps.validator.services.validation_service.fetch_page", return_value=html
    )


def test_process_valid_organization(mocker):
    _patch_fetch(mocker, fx.ORG_VALID)
    user = UserFactory()
    job = ValidationJob.objects.create(user=user, url="https://acme.example")

    status = process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert status == ValidationStatus.COMPLETED
    assert job.status == ValidationStatus.COMPLETED
    assert job.total_schemas_found == 1
    assert job.total_errors == 0
    assert job.has_json_ld is True
    assert job.has_microdata is False
    schema = job.schemas.get()
    assert schema.schema_type == "Organization"
    assert schema.format == SchemaFormat.JSON_LD
    assert schema.is_valid is True
    assert schema.google_rich_result_eligible is True


def test_process_counts_errors_and_warnings(mocker):
    _patch_fetch(mocker, fx.PRODUCT_MISSING_IMAGE)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://shop.example")

    process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert job.total_schemas_found == 1
    assert job.total_errors >= 1  # missing image
    schema = job.schemas.get()
    assert schema.is_valid is False
    assert schema.issues.filter(field="image", severity="error").exists()


def test_process_malformed_json_ld(mocker):
    _patch_fetch(mocker, fx.MALFORMED_JSON_LD)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://b.example")

    process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert job.has_json_ld is True
    assert job.total_errors >= 1
    schema = job.schemas.get()
    assert schema.is_valid is False
    assert schema.issues.filter(severity="error").exists()


def test_process_microdata_and_rdfa(mocker):
    # One doc containing microdata; the JSON-LD/RDFa extractors return nothing.
    _patch_fetch(mocker, fx.MICRODATA_PRODUCT)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://m.example")

    process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert job.has_microdata is True
    assert job.has_json_ld is False
    schema = job.schemas.get()
    assert schema.format == SchemaFormat.MICRODATA
    assert schema.schema_type == "Product"


def test_process_no_structured_data(mocker):
    _patch_fetch(mocker, fx.NO_STRUCTURED_DATA)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://plain.example")

    process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert job.status == ValidationStatus.COMPLETED
    assert job.total_schemas_found == 0
    assert job.has_json_ld is False


def test_process_graph_creates_two_items(mocker):
    _patch_fetch(mocker, fx.GRAPH_MULTIPLE)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://graph.example")

    process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert job.total_schemas_found == 2
    assert set(job.schemas.values_list("schema_type", flat=True)) == {"Organization", "WebSite"}


def test_process_is_rerunnable(mocker):
    _patch_fetch(mocker, fx.ORG_VALID)
    job = ValidationJob.objects.create(user=UserFactory(), url="https://acme.example")

    process_validation(job_id=str(job.id))
    process_validation(job_id=str(job.id))  # second run must not duplicate

    assert SchemaItem.objects.filter(job=job).count() == 1


def test_fetch_failure_marks_job_failed(mocker):
    from apps.validator.exceptions import PageFetchError

    mocker.patch(
        "apps.validator.services.validation_service.fetch_page",
        side_effect=PageFetchError(message="boom"),
    )
    job = ValidationJob.objects.create(user=UserFactory(), url="https://dead.example")

    status = process_validation(job_id=str(job.id))

    job.refresh_from_db()
    assert status == ValidationStatus.FAILED
    assert job.status == ValidationStatus.FAILED
    assert "boom" in job.error_message


def test_process_missing_job_is_safe():
    import uuid

    assert process_validation(job_id=str(uuid.uuid4())) == "missing"


def test_submit_creates_pending_job(mocker):
    # on_commit won't fire inside the test transaction, so the job stays pending.
    _patch_fetch(mocker, fx.ORG_VALID)
    user = UserFactory()

    job = submit_validation(user=user, url="https://acme.example")

    assert job.status == ValidationStatus.PENDING
    assert job.user == user


def test_submit_dispatches_and_completes(mocker, django_capture_on_commit_callbacks):
    # Celery eager: once the transaction commits, the on_commit task runs inline.
    _patch_fetch(mocker, fx.ORG_VALID)
    user = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        job = submit_validation(user=user, url="https://acme.example")

    job.refresh_from_db()
    assert job.status == ValidationStatus.COMPLETED
    assert (
        SchemaIssue.objects.filter(schema_item__job=job).count()
        == job.total_errors + job.total_warnings
    )
