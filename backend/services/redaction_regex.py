"""Regex-based PII detection for emails and IPs, with GeoIP allowlist rules and consistent replacement mapping."""

import ipaddress
import re
from typing import Any

# Practical email pattern (balance recall vs false positives)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
)

# IPv4 with octet validation (0-255 per octet)
IPV4_PATTERN = re.compile(
    r"\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
)

# IPv6 candidate pattern; validate with ipaddress. Order matters: ":: in middle"
# must come before "ends with ::" to match e.g. 2600:1f18:1234::1 fully.
IPV6_PATTERN = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    r"|\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b"
    r"|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b"
    r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b",
)


def _valid_ipv6(candidate: str) -> bool:
    """Return True if candidate is a valid IPv6 address."""
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False


def detect_and_build_mapping(
    text: str,
    geoip_module: Any,
) -> tuple[str, dict[str, str]]:
    """
    Detect emails and IPs in text, build consistent replacement mapping, apply replacements.

    Returns (redacted_text, mapping).

    - Emails: replaced with user-001@example.com, user-002@example.com, etc.
    - Private IPs and allowlist IPs: left unchanged.
    - Public IPs not in allowlist: replaced from GeoIP pool (IPv4->IPv4, IPv6->IPv6).
    """
    mapping: dict[str, str] = {}
    email_counter = [0]  # mutable to allow increment in nested scope

    def next_email_replacement() -> str:
        email_counter[0] += 1
        return f"user-{email_counter[0]:03d}@example.com"

    # 1. Emails
    for m in EMAIL_PATTERN.finditer(text):
        orig = m.group(0)
        if orig not in mapping:
            mapping[orig] = next_email_replacement()

    # 2. IPv4
    for m in IPV4_PATTERN.finditer(text):
        ip_str = m.group(0)
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or geoip_module.is_in_allowlist(ip_str):
            continue
        if ip_str not in mapping:
            mapping[ip_str] = geoip_module.pick_replacement(ip_str)

    # 3. IPv6 (validate candidates; ipaddress handles parsing)
    for m in IPV6_PATTERN.finditer(text):
        ip_str = m.group(0)
        if not _valid_ipv6(ip_str):
            continue
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or geoip_module.is_in_allowlist(ip_str):
            continue
        if ip_str not in mapping:
            mapping[ip_str] = geoip_module.pick_replacement(ip_str)

    # 4. Apply replacements: longest first to avoid substring collisions
    items = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    redacted = text
    for orig, repl in items:
        redacted = redacted.replace(orig, repl)

    return redacted, mapping
