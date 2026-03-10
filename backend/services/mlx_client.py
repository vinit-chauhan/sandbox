"""
MLX LLM provider using mlx_lm.server (OpenAI-compatible API).

Start the server with: mlx_lm.server --model <model> --port 8080
The backend connects via MLX_BASE_URL (default http://localhost:8080).

Set MLX_MODEL to the same model name you started the server with.
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

from services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

MLX_BASE_URL = os.getenv("MLX_BASE_URL", "http://localhost:8080")
MLX_MODEL = os.getenv("MLX_MODEL", "mlx-community/Qwen3.5-9B-MLX-4bit")
TIMEOUT = float(os.getenv("MLX_TIMEOUT", "120"))


class MLXProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "mlx"

    def _resolve_model(self) -> str:
        if MLX_MODEL:
            return MLX_MODEL
        return "default"

    async def chat(
        self,
        messages: list[dict],
        model: str,
        format_schema: dict | None = None,
    ) -> dict:
        model_name = self._resolve_model()
        payload: dict = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            # Disable thinking — reasoning tokens waste time and aren't used.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if format_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        logger.debug("MLX chat request: model=%s, msgs=%d",
                     model_name, len(messages))
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{MLX_BASE_URL}/v1/chat/completions", json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        logger.debug("MLX response length: %d chars", len(content))
        return {"message": {"content": content}}

    async def stream_chat(
        self, messages: list[dict], model: str
    ) -> AsyncGenerator[str, None]:
        model_name = self._resolve_model()
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            # Disable thinking for streaming — reasoning tokens go to a separate
            # field and are never shown, causing the connection to sit idle.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        logger.info("MLX stream start: model=%s", model_name)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{MLX_BASE_URL}/v1/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    payload_str = line[6:]
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{MLX_BASE_URL}/v1/models")
                return resp.status_code == 200
        except Exception:
            logger.warning("MLX health check failed", exc_info=True)
            return False
