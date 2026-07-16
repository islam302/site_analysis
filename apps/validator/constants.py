"""Constants for the structured-data validator."""
from django.db import models


class ValidationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class SchemaFormat(models.TextChoices):
    JSON_LD = "json-ld", "JSON-LD"
    MICRODATA = "microdata", "Microdata"
    RDFA = "rdfa", "RDFa"


class IssueSeverity(models.TextChoices):
    ERROR = "error", "Error"
    WARNING = "warning", "Warning"
    INFO = "info", "Info"


# Marker key injected by the JSON-LD extractor for a block that failed to parse.
# It flows through as a "schema" so the failure is surfaced as an error issue.
PARSE_ERROR_KEY = "@parseError"

# Type used when a schema's @type is missing or unparseable.
UNKNOWN_TYPE = "Unknown"

# Fetch behaviour.
FETCH_TIMEOUT = 15  # seconds (per spec)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; SiteAnalysisValidator/1.0; +structured-data-check)"
)
