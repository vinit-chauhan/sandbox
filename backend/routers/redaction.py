"""Redaction API: POST /api/redact with SSE streaming, regex-first then LLM pipeline."""

import json
import logging
import os

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas import RedactRequest
from services import geoip
from services import redaction_regex
from services.llm_provider import get_provider
from services.redaction_llm import extract_pii_mapping

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")


@router.post("/redact")
async def redact(request: RedactRequest):
    """Stream SSE events: progress updates, then final redacted result with mapping."""

    async def event_stream():
        text = request.text
        warning = None

        yield f"data: {json.dumps({'step': 'regex', 'progress': 10})}\n\n"

        text_after_regex, mapping = redaction_regex.detect_and_build_mapping(
            text, geoip
        )
        logger.info("Regex redaction found %d PII items", len(mapping))
        yield f"data: {json.dumps({'step': 'regex', 'progress': 40})}\n\n"

        provider = get_provider()
        llm_ok = provider.is_available()
        logger.info(
            "LLM provider %s available: %s", provider.name, llm_ok
        )

        if not llm_ok:
            warning = (
                f"{provider.name.capitalize()} unavailable; LLM detection skipped. "
                "Only regex redaction applied."
            )
            redacted_text = text_after_regex
        else:
            yield f"data: {json.dumps({'step': 'llm', 'progress': 50})}\n\n"

            try:
                mapping_before_llm = dict(mapping)
                mapping = await extract_pii_mapping(
                    text_after_regex, mapping, model=MODEL_NAME
                )

                new_items = [
                    (o, r) for o, r in mapping.items() if o not in mapping_before_llm
                ]
                new_items.sort(key=lambda x: len(x[0]), reverse=True)
                redacted_text = text_after_regex
                for orig, repl in new_items:
                    if orig in text_after_regex:
                        redacted_text = redacted_text.replace(orig, repl)
            except (httpx.HTTPError, httpx.RequestError, Exception) as exc:
                logger.error("LLM redaction failed: %s", exc, exc_info=True)
                warning = (
                    f"{provider.name.capitalize()} error; LLM detection skipped. "
                    "Only regex redaction applied."
                )
                redacted_text = text_after_regex

        logger.info(
            "Redaction complete: %d total mappings, warning=%s",
            len(mapping),
            warning,
        )
        yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'redacted_text': redacted_text, 'mapping': mapping, 'warning': warning})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
