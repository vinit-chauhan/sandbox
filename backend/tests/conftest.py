"""Shared pytest fixtures for backend tests."""

import os

# Use bundled GeoIP data for tests to avoid network fetches
os.environ["GEOIP_USE_BUNDLED"] = "1"
