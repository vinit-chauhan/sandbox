"""
Ollama LLM provider.

Uses the Ollama REST API at OLLAMA_BASE_URL (default http://localhost:11434).
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

from services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))


class OllamaProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "ollama"

    async def chat(
        self,
        messages: list[dict],
        model: str,
        format_schema: dict | None = None,
    ) -> dict:
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if format_schema is not None:
            payload["format"] = format_schema

        logger.debug("Ollama chat request: model=%s, msgs=%d",
                     model, len(messages))
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat", json=payload
            )
            response.raise_for_status()
            data = response.json()

        logger.debug(
            "Ollama response length: %d chars",
            len(data.get("message", {}).get("content", "")),
        )
        return data

    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[str, None]:
        logger.info("Ollama stream start: model=%s", model)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
                return resp.status_code == 200
        except Exception:
            logger.warning("Ollama health check failed", exc_info=True)
            return False
