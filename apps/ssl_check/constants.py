"""Constants for the SSL/TLS check domain."""
from django.db import models


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


# (display label, sslyze scan_result attribute, is_insecure_protocol)
PROTOCOL_SCANS = (
    ("SSL 2.0", "ssl_2_0_cipher_suites", True),
    ("SSL 3.0", "ssl_3_0_cipher_suites", True),
    ("TLS 1.0", "tls_1_0_cipher_suites", True),
    ("TLS 1.1", "tls_1_1_cipher_suites", True),
    ("TLS 1.2", "tls_1_2_cipher_suites", False),
    ("TLS 1.3", "tls_1_3_cipher_suites", False),
)
