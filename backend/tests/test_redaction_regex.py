"""Redaction regex tests (DET-01, DET-02, DET-03, DET-04, DET-06)."""

import pytest

from services.redaction_regex import detect_and_build_mapping

# Use real geoip module; conftest sets GEOIP_USE_BUNDLED=1
try:
    from services import geoip
    _geoip_available = True
except Exception:
    geoip = None
    _geoip_available = False

requires_geoip = pytest.mark.skipif(not _geoip_available, reason="GeoIP module failed to load")


@requires_geoip
def test_email_detection():
    """Text with email gets replaced with user-NNN@example.com."""
    text = "Contact admin@foo.com for help"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "admin@foo.com" not in out
    assert "user-001@example.com" in out
    assert mapping.get("admin@foo.com") == "user-001@example.com"


@requires_geoip
def test_private_ip_unchanged():
    """10.0.0.1, 172.16.0.1, 192.168.1.1 remain in output."""
    text = "Hosts 10.0.0.1, 172.16.0.1, 192.168.1.1 connected"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "10.0.0.1" in out
    assert "172.16.0.1" in out
    assert "192.168.1.1" in out
    assert "10.0.0.1" not in mapping
    assert "172.16.0.1" not in mapping
    assert "192.168.1.1" not in mapping


@requires_geoip
def test_allowlist_ip_unchanged():
    """IP from GeoIP allowlist (e.g. 1.128.0.1) remains."""
    text = "From 1.128.0.1 we received the request"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "1.128.0.1" in out
    assert "1.128.0.1" not in mapping


@requires_geoip
def test_public_ip_replaced():
    """Public IP not in allowlist (e.g. 8.8.8.8) replaced with IP from pool."""
    text = "Query to 8.8.8.8 failed"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "8.8.8.8" not in out
    repl = mapping.get("8.8.8.8")
    assert repl is not None
    assert repl != "8.8.8.8"
    assert geoip.is_in_allowlist(repl) is True


@requires_geoip
def test_consistent_mapping():
    """Same email appears twice; both get same replacement. Same public IP twice; both get same replacement."""
    text = "User bob@test.com logged from 8.8.4.4; bob@test.com later queried 8.8.4.4 again"
    out, mapping = detect_and_build_mapping(text, geoip)
    repl_email = mapping.get("bob@test.com")
    repl_ip = mapping.get("8.8.4.4")
    assert repl_email is not None
    assert repl_ip is not None
    assert out.count(repl_email) == 2
    assert out.count(repl_ip) == 2
    assert "bob@test.com" not in out
    assert "8.8.4.4" not in out


@requires_geoip
def test_phone_number_detection():
    """Phone numbers are detected and replaced consistently."""
    text = "Call +1 (555) 123-4567 or 555-987-6543 for support"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "+1 (555) 123-4567" not in out
    assert "555-987-6543" not in out
    assert "+1-555-000-0001" in out
    assert "+1-555-000-0002" in out


@requires_geoip
def test_phone_not_matching_dates():
    """Dates and timestamps should not be detected as phone numbers."""
    text = "Event on 2024-01-15 at 12:34:56"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert out == text
    assert len(mapping) == 0


@requires_geoip
def test_phone_not_matching_hashes():
    """SHA/hex hashes should not be detected as phone numbers."""
    text = "Commit 41c7e5714a91d17dea111575398d5d1ac merged"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert out == text
    assert len(mapping) == 0


@requires_geoip
def test_ipv6():
    """IPv6 public address replaced; IPv6 from allowlist unchanged."""
    # 2a02:cf40::1 is in allowlist (2a02:cf40::/29)
    # 2600:1f18:1234::1 is public, not in allowlist
    text = "Allowlist 2a02:cf40::1 and public 2600:1f18:1234::1"
    out, mapping = detect_and_build_mapping(text, geoip)
    assert "2a02:cf40::1" in out
    assert "2a02:cf40::1" not in mapping
    assert "2600:1f18:1234::1" not in out
    repl = mapping.get("2600:1f18:1234::1")
    assert repl is not None
    assert ":" in repl  # IPv6 format
    assert geoip.is_in_allowlist(repl) is True
