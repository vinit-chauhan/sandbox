"""Redaction API tests: POST /api/redact returns SSE with progress and final result."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import redaction

# Minimal app with only redaction router to avoid chromadb/rag imports in test env
app = FastAPI()
app.include_router(redaction.router)


@pytest.fixture
def client():
    return TestClient(app)


def _parse_last_sse_data(response_text: str) -> dict:
    """Extract last SSE data payload as dict."""
    lines = response_text.strip().split("\n")
    data_lines = [l for l in lines if l.startswith("data: ")]
    if not data_lines:
        return {}
    last = data_lines[-1]
    payload = last.split(" ", 1)[1]
    return json.loads(payload)


def test_redact_returns_200_and_sse(client):
    """Valid request returns 200 and SSE stream with done event."""
    r = client.post("/api/redact", json={"text": "hello world"})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    d = _parse_last_sse_data(r.text)
    assert d.get("step") == "done"
    assert d.get("progress") == 100
    assert "redacted_text" in d
    assert "mapping" in d


def test_email_redacted(client):
    """Text with email is redacted."""
    r = client.post(
        "/api/redact",
        json={"text": "Contact user@test.com for help"},
    )
    assert r.status_code == 200
    d = _parse_last_sse_data(r.text)
    redacted = d.get("redacted_text", "")
    assert "user@test.com" not in redacted
    assert "user-001@example.com" in redacted
    assert d.get("mapping", {}).get("user@test.com") == "user-001@example.com"


def test_private_ip_unchanged(client):
    """Private IPs remain unchanged in output."""
    r = client.post(
        "/api/redact",
        json={"text": "From 192.168.1.1 and 10.0.0.1"},
    )
    assert r.status_code == 200
    d = _parse_last_sse_data(r.text)
    redacted = d.get("redacted_text", "")
    assert "192.168.1.1" in redacted
    assert "10.0.0.1" in redacted


def test_mapping_consistent(client):
    """Mapping included and consistent with redacted text."""
    r = client.post(
        "/api/redact",
        json={"text": "user@test.com and 8.8.8.8 and user@test.com again"},
    )
    assert r.status_code == 200
    d = _parse_last_sse_data(r.text)
    redacted = d.get("redacted_text", "")
    mapping = d.get("mapping", {})

    # Email replaced consistently
    assert "user@test.com" not in redacted
    repl = mapping.get("user@test.com")
    assert repl
    assert redacted.count(repl) == 2

    # Public IP replaced
    assert "8.8.8.8" not in redacted
    assert "8.8.8.8" in mapping
