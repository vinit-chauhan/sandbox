"""Regex-based PII detection for emails, phone numbers, and IPs, with GeoIP allowlist rules and consistent replacement mapping."""

import ipaddress
import re
from typing import Any

# Practical email pattern (balance recall vs false positives)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
)

# Phone number patterns — covers common formats:
#   +1 (555) 123-4567, +1-555-123-4567, 555-123-4567, (555) 123-4567
#   +44 20 7946 0958, +91-98765-43210
# Uses [ \t] instead of \s to prevent matching across line boundaries.
# Requires at least one dash, space, or paren as separator (dots excluded to avoid IP collisions).
PHONE_PATTERN = re.compile(
    r"(?<![.\d])"                         # no digit or dot before (avoids IP fragments)
    r"(?:\+\d{1,3}[- \t]?)?"             # optional country code
    r"(?:\(?\d{2,4}\)?[- \t]?)?"         # optional area code
    r"\d{3,5}[- \t]?\d{3,5}"            # core number
    r"(?![.\d])",                         # no digit or dot after
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


def _looks_like_phone(candidate: str, text: str, start: int, end: int) -> bool:
    """Filter out false positives from the phone regex."""
    stripped = candidate.strip()
    if "\n" in stripped or "\r" in stripped:
        return False
    digits = re.sub(r"\D", "", stripped)
    if len(digits) < 7 or len(digits) > 15:
        return False
    # Must have at least one real phone separator (dash, space, paren, plus)
    if not re.search(r"[+() \t\-]", stripped):
        return False
    # Reject if adjacent to hex letters (hash fragment)
    if start > 0 and text[start - 1] in "abcdefABCDEF":
        return False
    if end < len(text) and text[end] in "abcdefABCDEF":
        return False
    # Reject date-like: 2024-01-15
    if re.fullmatch(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", stripped):
        return False
    # Reject time-like: 12:34:56
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", stripped):
        return False
    return True


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
    - Phone numbers: replaced with +1-555-000-0001, +1-555-000-0002, etc.
    - Private IPs and allowlist IPs: left unchanged.
    - Public IPs not in allowlist: replaced from GeoIP pool (IPv4->IPv4, IPv6->IPv6).
    """
    mapping: dict[str, str] = {}
    email_counter = [0]
    phone_counter = [0]

    def next_email_replacement() -> str:
        email_counter[0] += 1
        return f"user-{email_counter[0]:03d}@example.com"

    def next_phone_replacement() -> str:
        phone_counter[0] += 1
        return f"+1-555-000-{phone_counter[0]:04d}"

    # 1. Emails
    for m in EMAIL_PATTERN.finditer(text):
        orig = m.group(0)
        if orig not in mapping:
            mapping[orig] = next_email_replacement()

    # 2. Phone numbers
    for m in PHONE_PATTERN.finditer(text):
        orig = m.group(0).strip()
        if not orig or not _looks_like_phone(orig, text, m.start(), m.end()):
            continue
        if orig not in mapping:
            mapping[orig] = next_phone_replacement()

    # 3. IPv4
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

    # 4. IPv6
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

    # 5. Apply replacements: longest first to avoid substring collisions
    items = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    redacted = text
    for orig, repl in items:
        redacted = redacted.replace(orig, repl)

    return redacted, mapping


def detect_pii(text: str, geoip_module: Any) -> dict[str, str]:
    """Detect emails, phone numbers, and IPs. Return mapping without applying replacements."""
    mapping: dict[str, str] = {}
    email_counter = [0]
    phone_counter = [0]

    def next_email_replacement() -> str:
        email_counter[0] += 1
        return f"user-{email_counter[0]:03d}@example.com"

    def next_phone_replacement() -> str:
        phone_counter[0] += 1
        return f"+1-555-000-{phone_counter[0]:04d}"

    for m in EMAIL_PATTERN.finditer(text):
        orig = m.group(0)
        if orig not in mapping:
            mapping[orig] = next_email_replacement()

    for m in PHONE_PATTERN.finditer(text):
        orig = m.group(0).strip()
        if not orig or not _looks_like_phone(orig, text, m.start(), m.end()):
            continue
        if orig not in mapping:
            mapping[orig] = next_phone_replacement()

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

    return mapping


def apply_mapping(text: str, mapping: dict[str, str]) -> str:
    """Apply a replacement mapping to text, longest-first to avoid substring collisions."""
    items = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    result = text
    for orig, repl in items:
        result = result.replace(orig, repl)
    return result
