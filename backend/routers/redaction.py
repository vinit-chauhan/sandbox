"""Redaction API: POST /api/redact with SSE streaming, regex + LLM pipeline."""

import asyncio
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

    chunk_events: asyncio.Queue[dict] = asyncio.Queue()

    def _on_chunk_progress(completed: int, total: int):
        pct = 50 + int((completed / total) * 45)
        chunk_events.put_nowait({"step": "llm", "progress": pct, "chunk": completed, "total_chunks": total})

    async def event_stream():
        original_text = request.text
        warning = None

        yield f"data: {json.dumps({'step': 'regex', 'progress': 10})}\n\n"

        regex_mapping = redaction_regex.detect_pii(original_text, geoip)
        logger.info("Regex detection found %d PII items", len(regex_mapping))
        yield f"data: {json.dumps({'step': 'regex', 'progress': 40})}\n\n"

        provider = get_provider()
        llm_ok = provider.is_available()
        logger.info("LLM provider %s available: %s", provider.name, llm_ok)

        llm_mapping: dict[str, str] = {}

        if not llm_ok:
            warning = (
                f"{provider.name.capitalize()} unavailable; LLM detection skipped. "
                "Only regex redaction applied."
            )
        else:
            yield f"data: {json.dumps({'step': 'llm', 'progress': 50})}\n\n"

            try:
                task = asyncio.create_task(
                    extract_pii_mapping(
                        original_text, model=MODEL_NAME,
                        on_chunk_progress=_on_chunk_progress,
                    )
                )

                while not task.done():
                    try:
                        event = chunk_events.get_nowait()
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(0.2)

                llm_mapping = task.result()

                while not chunk_events.empty():
                    event = chunk_events.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"

                logger.info("LLM detection found %d PII items", len(llm_mapping))
            except (httpx.HTTPError, httpx.RequestError, Exception) as exc:
                logger.error("LLM redaction failed: %s", exc, exc_info=True)
                warning = (
                    f"{provider.name.capitalize()} error; LLM detection skipped. "
                    "Only regex redaction applied."
                )

        mapping = {**llm_mapping, **regex_mapping}
        redacted_text = redaction_regex.apply_mapping(original_text, mapping)

        logger.info(
            "Redaction complete: %d regex + %d llm = %d total mappings, warning=%s",
            len(regex_mapping),
            len(llm_mapping),
            len(mapping),
            warning,
        )
        yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'redacted_text': redacted_text, 'mapping': mapping, 'warning': warning})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
