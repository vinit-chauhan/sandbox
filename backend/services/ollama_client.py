"""
Ollama LLM provider.

Uses the Ollama REST API at OLLAMA_BASE_URL (default http://localhost:11434).
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

from services.llm_provider import LLMProvider, StreamEvent, StreamEventType

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

    async def stream_chat_with_thinking(
        self, messages: list[dict], model: str, enable_thinking: bool = False
    ) -> AsyncGenerator[StreamEvent, None]:
        if not enable_thinking:
            async for token in self.stream_chat(messages, model):
                yield StreamEvent(type=StreamEventType.CONTENT, text=token)
            return

        logger.info("Ollama stream (thinking) start: model=%s", model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": True,
        }
        # State machine to parse <think>...</think> tags from streamed content.
        # Ollama embeds thinking in the content with these tags.
        inside_think = False
        buffer = ""

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if not token:
                        continue

                    buffer += token
                    while buffer:
                        if inside_think:
                            end_idx = buffer.find("</think>")
                            if end_idx == -1:
                                # Could be partial tag — hold back last 8 chars
                                if len(buffer) > 8:
                                    yield StreamEvent(type=StreamEventType.THINKING, text=buffer[:-8])
                                    buffer = buffer[-8:]
                                break
                            # Emit everything before </think> as thinking
                            if end_idx > 0:
                                yield StreamEvent(type=StreamEventType.THINKING, text=buffer[:end_idx])
                            buffer = buffer[end_idx + 8:]
                            inside_think = False
                        else:
                            start_idx = buffer.find("<think>")
                            if start_idx == -1:
                                # Could be partial tag — hold back last 7 chars
                                if len(buffer) > 7:
                                    yield StreamEvent(type=StreamEventType.CONTENT, text=buffer[:-7])
                                    buffer = buffer[-7:]
                                break
                            # Emit everything before <think> as content
                            if start_idx > 0:
                                yield StreamEvent(type=StreamEventType.CONTENT, text=buffer[:start_idx])
                            buffer = buffer[start_idx + 7:]
                            inside_think = True

        # Flush remaining buffer
        if buffer:
            evt_type = StreamEventType.THINKING if inside_think else StreamEventType.CONTENT
            yield StreamEvent(type=evt_type, text=buffer)

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
                return resp.status_code == 200
        except Exception:
            logger.warning("Ollama health check failed", exc_info=True)
            return False
