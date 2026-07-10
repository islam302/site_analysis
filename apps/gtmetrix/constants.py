"""Enumerations and mappings for the GTmetrix domain."""
from django.db import models


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


# GTmetrix test lifecycle states (data.attributes.state on the test resource).
TEST_STATE_COMPLETED = "completed"
TEST_STATE_ERROR = "error"

# GTmetrix report attribute -> model field. Timing values are milliseconds.
REPORT_ATTR_TO_FIELD = {
    "gtmetrix_grade": "gtmetrix_grade",
    "performance_score": "performance_score",
    "structure_score": "structure_score",
    "first_contentful_paint": "first_contentful_paint",
    "largest_contentful_paint": "largest_contentful_paint",
    "cumulative_layout_shift": "cumulative_layout_shift",
    "total_blocking_time": "total_blocking_time",
    "time_to_interactive": "time_to_interactive",
    "speed_index": "speed_index",
    "onload_time": "onload_time",
    "fully_loaded_time": "fully_loaded_time",
    "page_bytes": "page_bytes",
    "page_requests": "page_requests",
}
