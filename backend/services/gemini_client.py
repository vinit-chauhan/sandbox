"""
Gemini LLM provider using the google-genai SDK.

Required env vars:
  GEMINI_API_KEY   — Google AI API key
  GEMINI_MODEL     — model name (default: gemini-2.0-flash)
"""

import logging
import os
from typing import AsyncGenerator

from google import genai
from google.genai import types

from services.llm_provider import LLMProvider, StreamEvent, StreamEventType

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _build_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY env var is required for Gemini provider")
    return genai.Client(api_key=GEMINI_API_KEY)


def _messages_to_gemini(
    messages: list[dict],
) -> tuple[str | None, list[types.Content]]:
    """Convert OpenAI-style messages to Gemini content list.

    Returns (system_instruction, contents).
    """
    system_instruction = None
    contents: list[types.Content] = []

    for msg in messages:
        role = msg["role"]
        text = msg["content"]
        if role == "system":
            system_instruction = text
        elif role == "assistant":
            contents.append(
                types.Content(role="model", parts=[types.Part.from_text(text=text)])
            )
        else:
            contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=text)])
            )

    return system_instruction, contents


class GeminiProvider(LLMProvider):
    def __init__(self):
        self._client = _build_client()

    @property
    def name(self) -> str:
        return "gemini"

    def _resolve_model(self, model: str) -> str:
        """Always use GEMINI_MODEL — ignore Ollama-style model names."""
        if not model or ":" in model:
            return GEMINI_MODEL
        return model

    async def chat(
        self,
        messages: list[dict],
        model: str,
        format_schema: dict | None = None,
    ) -> dict:
        model_name = self._resolve_model(model)
        system_instruction, contents = _messages_to_gemini(messages)

        config_kwargs: dict = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if format_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = format_schema

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        logger.debug("Gemini chat: model=%s, msgs=%d", model_name, len(messages))
        response = await self._client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        content = response.text or ""
        logger.debug("Gemini response: %d chars", len(content))
        return {"message": {"content": content}}

    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[str, None]:
        model_name = self._resolve_model(model)
        system_instruction, contents = _messages_to_gemini(messages)

        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        logger.info("Gemini stream start: model=%s", model_name)
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            text = chunk.text
            if text:
                yield text

    async def stream_chat_with_thinking(
        self, messages: list[dict], model: str, enable_thinking: bool = False
    ) -> AsyncGenerator[StreamEvent, None]:
        model_name = self._resolve_model(model)
        system_instruction, contents = _messages_to_gemini(messages)

        config_kwargs: dict = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if enable_thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=8192,
            )

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        logger.info("Gemini stream (thinking=%s) start: model=%s", enable_thinking, model_name)
        async for chunk in await self._client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, "thought") and part.thought:
                        yield StreamEvent(type=StreamEventType.THINKING, text=part.text)
                    elif part.text:
                        yield StreamEvent(type=StreamEventType.CONTENT, text=part.text)

    def is_available(self) -> bool:
        if not GEMINI_API_KEY:
            return False
        try:
            pager = self._client.models.list(config={"page_size": 1})
            first = next(iter(pager), None)
            return first is not None
        except Exception:
            logger.warning("Gemini health check failed", exc_info=True)
            return False
