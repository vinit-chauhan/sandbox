import os
import json
from typing import AsyncGenerator

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


async def chat(
    messages: list[dict], model: str, format_schema: dict | None = None
) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if format_schema is not None:
        payload["format"] = format_schema
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def stream_chat(messages: list[dict], model: str) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient(timeout=None) as client:
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
