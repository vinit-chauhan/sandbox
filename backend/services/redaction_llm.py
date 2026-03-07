"""
LLM-based PII extraction for redaction. Extracts hostnames, usernames, and paths
containing usernames from log text using the configured LLM provider with
structured JSON format.
"""

import json
import logging
import os

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

SYSTEM_PROMPT = """\
You extract PII from log text. Return ONLY a JSON object with three arrays:
- hostnames: server names, FQDNs (e.g. "prod-db.acme.com")
- usernames: login names (e.g. "jsmith")
- paths_with_usernames: file paths that contain a username (e.g. "/home/jsmith/logs")

If a category has nothing, use an empty array [].
Do NOT include IPs or emails (those are handled separately)."""

FEW_SHOT_EXAMPLE = """\
Log text:
2024-01-15 ERROR on web-prod-03.internal: user alice.wu failed auth at /home/alice.wu/app/config

Output:
{"hostnames": ["web-prod-03.internal"], "usernames": ["alice.wu"], "paths_with_usernames": ["/home/alice.wu/app/config"]}"""


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


async def extract_pii_mapping(
    text: str,
    model: str | None = None,
) -> dict[str, str]:
    """
    Extract PII from text using LLM, assign natural-looking replacements.
    Returns a standalone mapping (caller merges with regex mapping).
    Retries once on parse failure.
    """
    model = model or os.getenv("MODEL_NAME", "qwen2.5:7b")

    provider = get_provider()
    logger.info("PII extraction: provider=%s model=%s", provider.name, model)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Log text:\n{FEW_SHOT_EXAMPLE.split('Log text:')[1].split('Output:')[0].strip()}\n"},
        {"role": "assistant", "content": FEW_SHOT_EXAMPLE.split("Output:\n")[1].strip()},
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

            if not content:
                logger.warning("Empty LLM response (attempt %d)", attempt)
                continue

            parsed = json.loads(content)

            if not isinstance(parsed, dict):
                logger.warning("LLM returned non-object JSON (attempt %d): %s", attempt, type(parsed).__name__)
                continue

            mapping = _build_mapping_from_parsed(parsed)
            logger.info("PII extraction complete: %d mappings (attempt %d)", len(mapping), attempt)
            return mapping

        except json.JSONDecodeError as exc:
            logger.warning(
                "JSON parse failed (attempt %d/%d): %s — raw: %.300s",
                attempt, MAX_RETRIES, exc, content,
            )
        except Exception as exc:
            logger.error("LLM call failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc, exc_info=True)
            break

    logger.warning("PII extraction failed after %d attempts, returning empty mapping", MAX_RETRIES)
    return {}
