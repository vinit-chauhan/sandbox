"""
LLM-based PII extraction for redaction. Extracts hostnames, usernames, and paths
containing usernames from log text using Ollama with structured JSON format.
"""

import json
import os

from services.ollama_client import chat

OLLAMA_PII_FORMAT_SCHEMA = {
    "type": "object",
    "properties": {
        "hostnames": {"type": "array", "items": {"type": "string"}},
        "usernames": {"type": "array", "items": {"type": "string"}},
        "paths_with_usernames": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["hostnames", "usernames", "paths_with_usernames"],
}

HOSTNAME_REPLACEMENTS = [
    "server-alpha.example.com",
    "node-beta.example.com",
    "worker-gamma.example.com",
]

USERNAME_REPLACEMENTS = ["john.doe", "alice.smith", "bob.jones"]


def _next_hostname(index: int) -> str:
    return HOSTNAME_REPLACEMENTS[index % len(HOSTNAME_REPLACEMENTS)]


def _next_username(index: int) -> str:
    return USERNAME_REPLACEMENTS[index % len(USERNAME_REPLACEMENTS)]


def _extract_username_from_path(path: str) -> str | None:
    """Extract username from path like /home/john.smith/logs or /Users/alice/data."""
    path = path.strip().rstrip("/")
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part in ("home", "Users", "var", "tmp") and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate and candidate not in ("root", "home", "var", "tmp"):
                return candidate
    return None


async def extract_pii_mapping(
    text: str,
    existing_mapping: dict[str, str],
    model: str | None = None,
) -> dict[str, str]:
    """
    Extract PII from log text using LLM, assign natural-looking replacements,
    merge into existing mapping. Returns updated mapping (never overwrites existing keys).
    """
    model = model or os.getenv("MODEL_NAME", "qwen2.5:7b")
    mapping = dict(existing_mapping)

    prompt = """Extract PII from this log text. Return JSON with:
- hostnames: list of hostnames (FQDNs, server names)
- usernames: list of usernames (login names, user identifiers)
- paths_with_usernames: list of full path strings that contain usernames (e.g. /home/john.smith/logs, /Users/alice/data)

Return unique values only. One per list item.
If nothing found for a category, return empty array []."""

    messages = [
        {"role": "user", "content": f"{prompt}\n\nLog text:\n{text}"},
    ]

    try:
        response = await chat(messages, model, format_schema=OLLAMA_PII_FORMAT_SCHEMA)
        content = response.get("message", {}).get("content", "")
        if not content:
            return mapping
        parsed = json.loads(content)
    except (ValueError, KeyError):
        return mapping

    hostname_idx = 0
    username_idx = 0

    for hostname in parsed.get("hostnames") or []:
        hostname = str(hostname).strip()
        if not hostname or hostname in mapping:
            continue
        mapping[hostname] = _next_hostname(hostname_idx)
        hostname_idx += 1

    for username in parsed.get("usernames") or []:
        username = str(username).strip()
        if not username or username in mapping:
            continue
        mapping[username] = _next_username(username_idx)
        username_idx += 1

    for path_str in parsed.get("paths_with_usernames") or []:
        path_str = str(path_str).strip()
        if not path_str:
            continue
        username = _extract_username_from_path(path_str)
        if username:
            if username not in mapping:
                mapping[username] = _next_username(username_idx)
                username_idx += 1
            redacted_path = path_str.replace(username, mapping[username])
            if path_str not in mapping:
                mapping[path_str] = redacted_path

    return mapping
