"""
LLM-based PII extraction for redaction. Extracts hostnames, usernames, and paths
containing usernames from log text using the configured LLM provider with
structured JSON format. Large inputs are automatically chunked.
"""

import json
import logging
import os
from typing import Callable

from services.llm_provider import get_provider

logger = logging.getLogger(__name__)

PII_FORMAT_SCHEMA = {
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

MAX_RETRIES = 2
CHUNK_LINES = 80

SYSTEM_PROMPT = """\
You extract PII from log text. Return ONLY a JSON object with three arrays:
- hostnames: server names, FQDNs, device names (e.g. "prod-db.acme.com")
- usernames: login names, user_name values, account names (e.g. "jsmith", "MSC.Dept")
- paths_with_usernames: file paths that contain a username (e.g. "/home/jsmith/logs")

Logs may be in any format: syslog, key=value pairs, JSON, etc.
Look for fields like user_name=, user=, account=, login=, hostname=, device_id=, etc.
Always return the JSON object even if a category is empty (use []).
Do NOT include IPs or emails (those are handled separately).
You MUST respond with ONLY a JSON object, no other text."""

FEW_SHOT_EXAMPLE_INPUT = """\
2024-01-15 ERROR on web-prod-03.internal: user alice.wu failed auth at /home/alice.wu/app/config
<189>date=2025-10-13 time=14:02:50 device_id=FW123 user_name="admin.ops" http_host="lb-prod.corp.local\""""
FEW_SHOT_EXAMPLE_OUTPUT = '{"hostnames": ["web-prod-03.internal", "lb-prod.corp.local"], "usernames": ["alice.wu", "admin.ops"], "paths_with_usernames": ["/home/alice.wu/app/config"]}'


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


def _build_mapping_from_parsed(parsed: dict) -> dict[str, str]:
    """Convert parsed LLM output into a replacement mapping."""
    mapping: dict[str, str] = {}
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


async def _extract_pii_raw(
    text: str, model: str
) -> dict:
    """Send a single chunk to the LLM and return raw parsed PII dict. Retries on failure."""
    provider = get_provider()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Log text:\n{FEW_SHOT_EXAMPLE_INPUT}\n"},
        {"role": "assistant", "content": FEW_SHOT_EXAMPLE_OUTPUT},
        {"role": "user", "content": f"Log text:\n{text}"},
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        content = ""
        try:
            response = await provider.chat(
                messages, model, format_schema=PII_FORMAT_SCHEMA
            )
            content = response.get("message", {}).get("content", "")
            logger.debug("LLM response (attempt %d): %.500s", attempt, content)

            if not content or not content.strip():
                logger.warning("Empty LLM response (attempt %d)", attempt)
                continue

            # Strip markdown fences (```json ... ```) that some models wrap around JSON
            stripped = content.strip()
            if stripped.startswith("```"):
                stripped = stripped.split("\n", 1)[-1]
                if stripped.endswith("```"):
                    stripped = stripped[:-3]
                content = stripped.strip()

            # raw_decode parses the first JSON value and ignores trailing data
            # (e.g. Llama EOS tokens, repeated outputs)
            decoder = json.JSONDecoder()
            start = content.find("{")
            if start == -1:
                logger.warning("No JSON object in response (attempt %d): %.300s", attempt, content)
                continue
            parsed, _ = decoder.raw_decode(content, start)

            if not isinstance(parsed, dict):
                logger.warning("LLM returned non-object JSON (attempt %d): %s", attempt, type(parsed).__name__)
                continue

            return parsed

        except json.JSONDecodeError as exc:
            logger.warning(
                "JSON parse failed (attempt %d/%d): %s — raw: %.300s",
                attempt, MAX_RETRIES, exc, content,
            )
        except Exception as exc:
            logger.error("LLM call failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc, exc_info=True)
            break

    return {"hostnames": [], "usernames": [], "paths_with_usernames": []}


async def extract_pii_mapping(
    text: str,
    model: str | None = None,
    on_chunk_progress: Callable[[int, int], None] | None = None,
) -> dict[str, str]:
    """
    Extract PII from text using LLM, assign natural-looking replacements.
    Large inputs are split into chunks of ~CHUNK_LINES lines each.
    on_chunk_progress(completed, total) is called after each chunk.
    """
    model = model or os.getenv("MODEL_NAME", "qwen2.5:7b")
    provider = get_provider()

    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    for i in range(0, len(lines), CHUNK_LINES):
        chunks.append("".join(lines[i : i + CHUNK_LINES]))

    logger.info(
        "PII extraction: provider=%s model=%s lines=%d chunks=%d",
        provider.name, model, len(lines), len(chunks),
    )

    all_hostnames: list[str] = []
    all_usernames: list[str] = []
    all_paths: list[str] = []

    for idx, chunk in enumerate(chunks):
        parsed = await _extract_pii_raw(chunk, model)
        all_hostnames.extend(parsed.get("hostnames") or [])
        all_usernames.extend(parsed.get("usernames") or [])
        all_paths.extend(parsed.get("paths_with_usernames") or [])
        logger.info("Chunk %d/%d done: %d hostnames, %d usernames, %d paths",
                     idx + 1, len(chunks),
                     len(parsed.get("hostnames") or []),
                     len(parsed.get("usernames") or []),
                     len(parsed.get("paths_with_usernames") or []))
        if on_chunk_progress:
            on_chunk_progress(idx + 1, len(chunks))

    merged = {
        "hostnames": all_hostnames,
        "usernames": all_usernames,
        "paths_with_usernames": all_paths,
    }
    mapping = _build_mapping_from_parsed(merged)
    logger.info("PII extraction complete: %d total mappings from %d chunks", len(mapping), len(chunks))
    return mapping
