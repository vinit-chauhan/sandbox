"""
Abstract LLM provider interface and factory.

Supports Ollama (local), MLX (local, Apple Silicon), and Gemini (cloud) backends.
Set LLM_PROVIDER env var to 'ollama', 'mlx', or 'gemini'.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator


class StreamEventType(str, Enum):
    THINKING = "thinking"
    CONTENT = "content"


@dataclass
class StreamEvent:
    type: StreamEventType
    text: str


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        format_schema: dict | None = None,
    ) -> dict:
        """Non-streaming chat. Returns {"message": {"content": "..."}}."""
        ...

    @abstractmethod
    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[str, None]:
        """Streaming chat. Yields token strings."""
        ...

    async def stream_chat_with_thinking(
        self, messages: list[dict], model: str, enable_thinking: bool = False
    ) -> AsyncGenerator[StreamEvent, None]:
        """Streaming chat with thinking support. Yields StreamEvent objects.

        Default implementation wraps stream_chat — all tokens as CONTENT events.
        Providers override this to support native thinking/reasoning modes.
        """
        async for token in self.stream_chat(messages, model):
            yield StreamEvent(type=StreamEventType.CONTENT, text=token)

    @abstractmethod
    def is_available(self) -> bool:
        """Quick health check — is the backend reachable?"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...


_provider_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the configured LLM provider (singleton)."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider_name == "gemini":
        from services.gemini_client import GeminiProvider

        _provider_instance = GeminiProvider()
    elif provider_name == "mlx":
        from services.mlx_client import MLXProvider

        _provider_instance = MLXProvider()
    else:
        from services.ollama_client import OllamaProvider

        _provider_instance = OllamaProvider()

    return _provider_instance
