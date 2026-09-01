from pydantic import BaseModel
from typing import Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[list[str]] = None
    history: list[Message] = []
    enable_thinking: bool = False


class DocumentInfo(BaseModel):
    id: str
    name: str


class RedactRequest(BaseModel):
    text: str


class RedactResponse(BaseModel):
    redacted_text: str
    mapping: dict[str, str]
    warning: str | None = None
