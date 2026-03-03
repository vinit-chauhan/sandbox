from pydantic import BaseModel
from typing import Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[list[str]] = None
    history: list[Message] = []


class DocumentInfo(BaseModel):
    id: str
    name: str
