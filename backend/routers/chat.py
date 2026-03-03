import os
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas import ChatRequest
from services import rag, ollama_client

router = APIRouter(prefix="/api")

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")


@router.post("/chat")
async def chat(request: ChatRequest):
    messages: list[dict] = []

    if request.document_ids:
        context = rag.query(request.document_ids, request.message, top_k=5)
        if context.strip():
            messages.append({
                "role": "system",
                "content": f"Answer using this context:\n\n{context}",
            })

    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.message})

    async def event_stream():
        async for token in ollama_client.stream_chat(messages, MODEL_NAME):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
