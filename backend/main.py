from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, documents, redaction

app = FastAPI(title="Local LLM Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(redaction.router)
