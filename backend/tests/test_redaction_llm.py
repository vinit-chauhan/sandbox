"""Tests for redaction_llm PII extraction (DET-05)."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.redaction_llm import extract_pii_mapping


pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.name = "test"
    provider.chat = AsyncMock()
    with patch("services.redaction_llm.get_provider", return_value=provider):
        yield provider


@pytest.mark.asyncio
async def test_llm_extracts_hostnames(mock_provider):
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": ["prod-server-01.internal", "db-master.example.org"],
                "usernames": [],
                "paths_with_usernames": [],
            })
        }
    }
    mapping = await extract_pii_mapping("Log from prod-server-01", "test-model")
    assert "prod-server-01.internal" in mapping
    assert mapping["prod-server-01.internal"] == "server-alpha.example.com"
    assert "db-master.example.org" in mapping
    assert mapping["db-master.example.org"] == "node-beta.example.com"


@pytest.mark.asyncio
async def test_llm_extracts_usernames(mock_provider):
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": [],
                "usernames": ["jsmith", "a.smith"],
                "paths_with_usernames": [],
            })
        }
    }
    mapping = await extract_pii_mapping("User jsmith logged in", "test-model")
    assert "jsmith" in mapping
    assert mapping["jsmith"] == "john.doe"
    assert "a.smith" in mapping
    assert mapping["a.smith"] == "alice.smith"


@pytest.mark.asyncio
async def test_llm_path_replacement(mock_provider):
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": [],
                "usernames": [],
                "paths_with_usernames": ["/home/jsmith/data/logs"],
            })
        }
    }
    mapping = await extract_pii_mapping("Log path /home/jsmith/data/logs", "test-model")
    assert "jsmith" in mapping
    assert mapping["jsmith"] == "john.doe"
    assert "/home/jsmith/data/logs" in mapping
    assert mapping["/home/jsmith/data/logs"] == "/home/john.doe/data/logs"


@pytest.mark.asyncio
async def test_consistent_mapping(mock_provider):
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": ["server-a", "server-a"],
                "usernames": [],
                "paths_with_usernames": [],
            })
        }
    }
    mapping = await extract_pii_mapping("text", "test-model")
    assert mapping["server-a"] == "server-alpha.example.com"
    assert len(mapping) == 1


@pytest.mark.asyncio
async def test_llm_standalone_mapping(mock_provider):
    """LLM produces its own mapping without any existing input."""
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": ["db.internal"],
                "usernames": [],
                "paths_with_usernames": [],
            })
        }
    }
    mapping = await extract_pii_mapping("text", "test-model")
    assert "db.internal" in mapping
    assert mapping["db.internal"] == "server-alpha.example.com"


@pytest.mark.asyncio
async def test_invalid_json_fallback(mock_provider):
    mock_provider.chat.return_value = {
        "message": {"content": "not valid json {{"}
    }
    mapping = await extract_pii_mapping("text", "test-model")
    assert mapping == {}


@pytest.mark.asyncio
async def test_path_with_Users_prefix(mock_provider):
    mock_provider.chat.return_value = {
        "message": {
            "content": json.dumps({
                "hostnames": [],
                "usernames": [],
                "paths_with_usernames": ["/Users/alice.smith/projects/log.txt"],
            })
        }
    }
    mapping = await extract_pii_mapping("Path /Users/alice.smith/projects/log.txt", "test-model")
    assert "alice.smith" in mapping
    assert "/Users/alice.smith/projects/log.txt" in mapping
    assert mapping["/Users/alice.smith/projects/log.txt"] == "/Users/john.doe/projects/log.txt"
