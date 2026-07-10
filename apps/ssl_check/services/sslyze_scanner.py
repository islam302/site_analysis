"""Local TLS scanner built on sslyze (no external API, no key).

``run_ssl_scan`` performs the handshakes against the target host itself and
returns a flat dict matching ``SSLReport`` fields, including a synthesised grade
(sslyze does not provide the Qualys letter grade, so we derive a simple one).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sslyze import (
    ScanCommandAttemptStatusEnum,
    Scanner,
    ServerNetworkLocation,
    ServerScanRequest,
    ServerScanStatusEnum,
)

from apps.ssl_check.constants import PROTOCOL_SCANS
from apps.ssl_check.exceptions import SSLScanError

logger = logging.getLogger("apps.ssl_check")


def _completed(attempt) -> bool:
    return (
        attempt is not None
        and attempt.status == ScanCommandAttemptStatusEnum.COMPLETED
        and attempt.result is not None
    )


def _synthesise_grade(*, protocols, vulnerabilities, expires_in_days, is_trusted) -> str:
    """Derive a coarse grade (A+/A/B/C/F/T) from the findings."""
    insecure_ssl = "SSL 2.0" in protocols or "SSL 3.0" in protocols
    serious_vuln = any(
        vulnerabilities.get(k)
        for k in ("heartbleed", "openssl_ccs_injection", "robot")
    )
    if insecure_ssl or serious_vuln:
        return "F"
    if is_trusted is False:
        return "T"  # certificate chain not trusted
    if expires_in_days is not None and expires_in_days < 0:
        return "F"  # expired certificate
    if "TLS 1.0" in protocols or "TLS 1.1" in protocols:
        return "B"
    minor_issue = vulnerabilities.get("tls_compression_crime") or vulnerabilities.get(
        "insecure_renegotiation"
    )
    if "TLS 1.3" in protocols and not minor_issue:
        return "A+"
    return "A"


def _parse(host: str, result) -> dict:
    sr = result.scan_result

    protocols, cipher_counts = [], {}
    for label, attr, _insecure in PROTOCOL_SCANS:
        attempt = getattr(sr, attr, None)
        if _completed(attempt):
            accepted = attempt.result.accepted_cipher_suites
            cipher_counts[label] = len(accepted)
            if accepted:
                protocols.append(label)

    subject = issuer = ""
    valid_from = valid_to = None
    expires_in = None
    is_trusted = None
    if _completed(sr.certificate_info):
        deployment = sr.certificate_info.result.certificate_deployments[0]
        leaf = deployment.received_certificate_chain[0]
        subject = leaf.subject.rfc4514_string()
        issuer = leaf.issuer.rfc4514_string()
        valid_from = leaf.not_valid_before_utc
        valid_to = leaf.not_valid_after_utc
        expires_in = (valid_to - datetime.now(tz=timezone.utc)).days
        is_trusted = any(
            getattr(pv, "was_validation_successful", False)
            for pv in deployment.path_validation_results
        )

    vulnerabilities: dict[str, bool] = {}
    hb = getattr(sr, "heartbleed", None)
    if _completed(hb):
        vulnerabilities["heartbleed"] = bool(hb.result.is_vulnerable_to_heartbleed)
    ccs = getattr(sr, "openssl_ccs_injection", None)
    if _completed(ccs):
        vulnerabilities["openssl_ccs_injection"] = bool(
            ccs.result.is_vulnerable_to_ccs_injection
        )
    robot = getattr(sr, "robot", None)
    if _completed(robot):
        vulnerabilities["robot"] = robot.result.robot_result.name.startswith("VULNERABLE")
    compression = getattr(sr, "tls_compression", None)
    if _completed(compression):
        vulnerabilities["tls_compression_crime"] = bool(
            compression.result.supports_compression
        )
    renegotiation = getattr(sr, "session_renegotiation", None)
    if _completed(renegotiation):
        vulnerabilities["insecure_renegotiation"] = not bool(
            renegotiation.result.supports_secure_renegotiation
        )

    grade = _synthesise_grade(
        protocols=protocols,
        vulnerabilities=vulnerabilities,
        expires_in_days=expires_in,
        is_trusted=is_trusted,
    )
    weak = "TLS 1.0" in protocols or "TLS 1.1" in protocols
    has_warnings = bool(
        weak
        or any(vulnerabilities.values())
        or is_trusted is False
        or (expires_in is not None and expires_in < 30)
    )

    return {
        "grade": grade,
        "has_warnings": has_warnings,
        "ip_address": getattr(result.server_location, "ip_address", "") or "",
        "server_name": host,
        "cert_subject": subject,
        "cert_issuer": issuer,
        "cert_valid_from": valid_from,
        "cert_valid_to": valid_to,
        "cert_expires_in_days": expires_in,
        "cert_is_trusted": is_trusted,
        "protocols": protocols,
        "vulnerabilities": vulnerabilities,
        "raw_response": {
            "protocols": protocols,
            "cipher_counts": cipher_counts,
            "certificate": {
                "subject": subject,
                "issuer": issuer,
                "valid_from": valid_from.isoformat() if valid_from else None,
                "valid_to": valid_to.isoformat() if valid_to else None,
                "expires_in_days": expires_in,
                "is_trusted": is_trusted,
            },
            "vulnerabilities": vulnerabilities,
        },
    }


def run_ssl_scan(*, host: str, port: int = 443) -> dict:
    """Scan ``host:port`` with sslyze and return parsed results.

    Raises:
        SSLScanError: the host could not be reached / handshake failed.
    """
    logger.info("SSL scan started", extra={"host": host, "port": port})
    request = ServerScanRequest(
        server_location=ServerNetworkLocation(hostname=host, port=port)
    )
    scanner = Scanner()
    scanner.queue_scans([request])

    result = next(iter(scanner.get_results()), None)
    if result is None:
        raise SSLScanError("No scan result returned.", extra={"host": host})
    if result.scan_status != ServerScanStatusEnum.COMPLETED:
        raise SSLScanError(
            f"Could not connect to {host}:{port}.",
            extra={"host": host, "scan_status": str(result.scan_status)},
        )

    parsed = _parse(host, result)
    logger.info("SSL scan finished", extra={"host": host, "grade": parsed["grade"]})
    return parsed
