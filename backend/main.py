import logging
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, documents, redaction

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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


@app.on_event("startup")
async def startup():
    provider_name = os.getenv("LLM_PROVIDER", "ollama")
    logger.info("Starting up — LLM provider: %s", provider_name)
    match provider_name:
        case "mlx":
            logger.info("Model: %s", os.getenv(
                "MLX_MODEL", "mlx-community/Qwen3.5-9B-MLX-4bit"))
        case "gemini":
            logger.info("Model: %s", os.getenv(
                "GEMINI_MODEL", "gemini-2.0-flash"))
        case "ollama":
            logger.info("Model: %s", os.getenv("MODEL_NAME", "qwen2.5:7b"))
        case _:
            logger.error("Invalid provider: %s", provider_name)
            raise ValueError(f"Invalid provider: {provider_name}")
