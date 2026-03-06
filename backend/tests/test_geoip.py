"""GeoIP allowlist tests (DET-03)."""

import pytest

from services.geoip import is_in_allowlist, pick_replacement


def test_allowlist_unchanged():
    """IP in allowlist (e.g. from 1.128.0.0/11) is reported as in_allowlist."""
    assert is_in_allowlist("1.128.0.1") is True
    assert is_in_allowlist("1.128.255.255") is True


def test_private_unchanged():
    """10.x, 172.16.x, 192.168.x are in_allowlist."""
    assert is_in_allowlist("10.0.0.1") is True
    assert is_in_allowlist("10.255.255.255") is True
    assert is_in_allowlist("172.16.0.1") is True
    assert is_in_allowlist("172.31.255.255") is True
    assert is_in_allowlist("192.168.1.1") is True
    assert is_in_allowlist("192.168.255.255") is True


def test_public_gets_replacement():
    """Public IP not in allowlist gets deterministic replacement from pool."""
    assert is_in_allowlist("8.8.8.8") is False
    r = pick_replacement("8.8.8.8")
    assert r != "8.8.8.8"
    assert is_in_allowlist(r) is True


def test_consistent_replacement():
    """Same IP passed to pick_replacement twice returns same result."""
    r1 = pick_replacement("8.8.4.4")
    r2 = pick_replacement("8.8.4.4")
    assert r1 == r2
