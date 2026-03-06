"""Redaction API: POST /api/redact with SSE streaming, regex-first then LLM pipeline."""

import json
import os

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas import RedactRequest
from services import geoip
from services import redaction_regex
from services.redaction_llm import extract_pii_mapping

router = APIRouter(prefix="/api")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")


def _ollama_available() -> bool:
    """Check if Ollama is reachable. Uses /api/tags for a quick health check."""
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


@router.post("/redact")
async def redact(request: RedactRequest):
    """Stream SSE events: progress updates, then final redacted result with mapping."""

    async def event_stream():
        text = request.text
        warning = None

        # (a) GeoIP init — import triggers it
        yield f"data: {json.dumps({'step': 'regex', 'progress': 10})}\n\n"

        # (b) Regex pipeline
        text_after_regex, mapping = redaction_regex.detect_and_build_mapping(
            text, geoip
        )
        yield f"data: {json.dumps({'step': 'regex', 'progress': 40})}\n\n"

        # (c) Ollama check
        ollama_ok = _ollama_available()

        if not ollama_ok:
            warning = (
                "Ollama unavailable; LLM detection skipped. "
                "Only regex redaction applied."
            )
            redacted_text = text_after_regex
        else:
            yield f"data: {json.dumps({'step': 'llm', 'progress': 50})}\n\n"

            try:
                # (d) LLM extraction and merge
                mapping_before_llm = dict(mapping)
                mapping = await extract_pii_mapping(
                    text_after_regex, mapping, model=MODEL_NAME
                )

                # Apply only LLM-added replacements (longest first to avoid collisions)
                new_items = [
                    (o, r) for o, r in mapping.items() if o not in mapping_before_llm
                ]
                new_items.sort(key=lambda x: len(x[0]), reverse=True)
                redacted_text = text_after_regex
                for orig, repl in new_items:
                    if orig in text_after_regex:
                        redacted_text = redacted_text.replace(orig, repl)
            except (httpx.HTTPError, httpx.RequestError):
                warning = (
                    "Ollama unavailable; LLM detection skipped. "
                    "Only regex redaction applied."
                )
                redacted_text = text_after_regex

        yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'redacted_text': redacted_text, 'mapping': mapping, 'warning': warning})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
