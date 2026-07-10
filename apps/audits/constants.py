"""Enumerations and WAVE mappings for the audits domain."""
from django.db import models


class AuditStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class IssueType(models.TextChoices):
    ERROR = "error", "Error"
    ALERT = "alert", "Alert"
    FEATURE = "feature", "Feature"
    STRUCTURAL = "structural", "Structural"
    CONTRAST = "contrast", "Contrast"


# WAVE response category key -> (our IssueType, audit total field).
# WAVE's ``structure`` category maps to our ``structural`` issue type.
WAVE_CATEGORY_MAP = {
    "error": (IssueType.ERROR, "total_errors"),
    "alert": (IssueType.ALERT, "total_alerts"),
    "feature": (IssueType.FEATURE, "total_features"),
    "structure": (IssueType.STRUCTURAL, "total_structural"),
    "contrast": (IssueType.CONTRAST, "total_contrast_errors"),
}

# Cost (in internal credits) of a single audit.
AUDIT_CREDIT_COST = 1
