"""GeoIP allowlist service: fetch allowed CIDR list, build replacement pools, provide allowlist check and deterministic replacement."""

import hashlib
import ipaddress
import logging
import os
from functools import lru_cache
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

GEOIP_URL = "https://raw.githubusercontent.com/elastic/elastic-package/main/internal/fields/_static/allowed_geo_ips.txt"
BUNDLED_PATH = Path(__file__).resolve().parent.parent / "data" / "allowed_geo_ips.txt"
MAX_HOSTS_PER_NETWORK = 256


def _fetch_geoip_content() -> str:
    """Fetch GeoIP list from GitHub. Returns content or empty string on failure."""
    if os.environ.get("GEOIP_USE_BUNDLED") == "1":
        return ""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(GEOIP_URL)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning("GeoIP fetch failed (%s), using bundled fallback", e)
        return ""


def _parse_cidr(content: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse CIDR lines from content. Skips empty lines and lines starting with #."""
    networks = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            net = ipaddress.ip_network(line, strict=False)
            networks.append(net)
        except ValueError:
            continue
    return networks


def _build_pool(
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> list[str]:
    """Build replacement pool: up to MAX_HOSTS_PER_NETWORK usable hosts per network."""
    pool: list[str] = []
    for net in networks:
        count = 0
        for host in net.hosts():
            if count >= MAX_HOSTS_PER_NETWORK:
                break
            pool.append(str(host))
            count += 1
    return pool


@lru_cache(maxsize=1)
def _load_geoip() -> tuple[
    list[ipaddress.IPv4Network | ipaddress.IPv6Network],
    list[str],
    list[str],
]:
    """Load allowlist networks and replacement pools. Runs once via lru_cache."""
    content = _fetch_geoip_content()
    if content:
        logger.info("GeoIP list: using fetched content from %s", GEOIP_URL)
    else:
        content = BUNDLED_PATH.read_text() if BUNDLED_PATH.exists() else ""
        logger.info("GeoIP list: using bundled fallback at %s", BUNDLED_PATH)

    networks = _parse_cidr(content)
    ipv4_networks = [n for n in networks if isinstance(n, ipaddress.IPv4Network)]
    ipv6_networks = [n for n in networks if isinstance(n, ipaddress.IPv6Network)]

    ipv4_pool = _build_pool(ipv4_networks)
    ipv6_pool = _build_pool(ipv6_networks)

    all_networks = ipv4_networks + ipv6_networks
    return all_networks, ipv4_pool, ipv6_pool


def is_in_allowlist(ip_str: str) -> bool:
    """True if IP is private or in any allowlist network."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_private:
        return True

    allowlist_networks, _, _ = _load_geoip()
    return any(ip in net for net in allowlist_networks)


def pick_replacement(original_ip: str) -> str:
    """Hash-based deterministic selection from same-version pool. Same IP always gets same replacement."""
    try:
        ip = ipaddress.ip_address(original_ip)
    except ValueError:
        raise ValueError(f"Invalid IP: {original_ip}")

    _, ipv4_pool, ipv6_pool = _load_geoip()

    if ip.version == 4:
        pool = ipv4_pool
    else:
        pool = ipv6_pool

    if not pool:
        raise ValueError(
            f"No replacement pool available for {ip.version == 4 and 'IPv4' or 'IPv6'}"
        )

    h = hashlib.sha256(original_ip.encode()).hexdigest()
    idx = int(h[:16], 16) % len(pool)
    return pool[idx]
