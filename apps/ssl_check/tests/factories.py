"""factory_boy factories and fixtures for the ssl_check app."""
from datetime import datetime, timezone

import factory

from apps.ssl_check.constants import ReportStatus
from apps.ssl_check.models import SSLReport
from apps.users.tests.factories import UserFactory


class SSLReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SSLReport

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    host = factory.Sequence(lambda n: f"example{n}.com")
    status = ReportStatus.PENDING


class CompletedSSLReportFactory(SSLReportFactory):
    status = ReportStatus.COMPLETED
    grade = "A+"
    has_warnings = False
    ip_address = "93.184.216.34"
    cert_subject = "CN=example.com"
    cert_issuer = "CN=Test CA"
    cert_expires_in_days = 120
    cert_is_trusted = True
    protocols = ["TLS 1.2", "TLS 1.3"]
    vulnerabilities = {"heartbleed": False, "robot": False}


def fake_ssl_scan_result(grade: str = "A+") -> dict:
    """Shape returned by ``run_ssl_scan`` (for mocking the service)."""
    return {
        "grade": grade,
        "has_warnings": False,
        "ip_address": "93.184.216.34",
        "server_name": "example.com",
        "cert_subject": "CN=example.com",
        "cert_issuer": "CN=Test CA",
        "cert_valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "cert_valid_to": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "cert_expires_in_days": 120,
        "cert_is_trusted": True,
        "protocols": ["TLS 1.2", "TLS 1.3"],
        "vulnerabilities": {"heartbleed": False, "robot": False},
        "raw_response": {"protocols": ["TLS 1.2", "TLS 1.3"]},
    }
