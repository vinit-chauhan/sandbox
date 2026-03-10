# Local LLM Chat with File Attachments

A self-hosted AI chat application that runs a Qwen model entirely on-device, lets you upload documents (PDF, DOCX, TXT, MD) and ask questions about them using RAG (Retrieval-Augmented Generation).

## Architecture

```
Host Machine
├── Ollama            (LLM inference — Metal/GPU)
└── MLX   (optional)  (Apple Silicon — faster on M-series Macs)

Docker Compose
├── ChromaDB          (vector store for document chunks)
├── Backend           (FastAPI — chat, upload, RAG orchestration)
└── Frontend          (React + Vite + Tailwind — served by Nginx)
```

The LLM provider (Ollama or MLX) runs natively on the host for full GPU acceleration. The Docker services reach it via `host.docker.internal`. Only port **80** is exposed to the host.

## Prerequisites — LLM Provider

The app needs a local LLM server running on your host machine. Pick **one** of the two providers below.

> **Apple Silicon recommendation:** Use **MLX** — it is purpose-built for the Apple Neural Engine / Metal and delivers noticeably faster token generation than Ollama on M-series Macs.

### Option A: MLX (Apple Silicon only)

1. **Install `mlx-lm`:**

```bash
# via pipx (recommended — no venv to manage)
pipx install mlx-lm

# or in a virtual environment
python3 -m venv .venv && source .venv/bin/activate && pip install mlx-lm
```

2. **Start the MLX server:**

```bash
# uses the helper script (default model: Qwen3.5-9B-MLX-4bit, port 8080)
./scripts/start-mlx.sh

# or start manually with a different model
mlx_lm.server --model mlx-community/Qwen3.5-9B-MLX-4bit --host 0.0.0.0 --port 8080
```

3. **Set the provider** when launching Docker (see Quick Start below):

```bash
LLM_PROVIDER=mlx docker compose up --build
```

You can customise the model and port with env vars:

```bash
MLX_MODEL=mlx-community/Qwen3.5-9B-MLX-4bit MLX_PORT=8080 LLM_PROVIDER=mlx docker compose up --build
```

### Option B: Ollama (macOS / Linux / Windows)

1. **Install Ollama** — download from [ollama.com](https://ollama.com/download).

2. **Pull a model:**

```bash
ollama pull qwen3.5:4b
```

3. **Start Ollama** so Docker containers can reach it. Ollama binds to `127.0.0.1` by default, which blocks connections from Docker's `host.docker.internal`. Set `OLLAMA_HOST=0.0.0.0` before starting:

```bash
# quick start (sets the env var and launches in one line)
OLLAMA_HOST=0.0.0.0 ollama run qwen3.5:4b

# or use the helper script (includes GPU tuning, warm-up, etc.)
./scripts/start-ollama.sh
```

Ollama is the default provider — no extra env vars needed when starting Docker.

## Quick Start

1. **Start your LLM provider** (see above).

2. **Start the Docker services:**

```bash
# Ollama (default)
docker compose up --build

# MLX
LLM_PROVIDER=mlx docker compose up --build
```

3. Open [http://localhost](http://localhost) in your browser.

## Swap Model

1. Pull the new model on your host: `ollama pull <model>`
2. Update `MODEL_NAME` in `docker-compose.yml`:

```yaml
environment:
  MODEL_NAME: qwen3:8b   # or any Ollama-supported model
```

3. Restart the backend: `docker compose restart backend`

## Project Structure

```
├── docker-compose.yml          # Orchestrates 3 Docker services
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app entry point
│   ├── schemas.py              # Pydantic request/response models
│   ├── routers/
│   │   ├── chat.py             # POST /api/chat (SSE streaming)
│   │   └── documents.py        # Upload, list, delete documents
│   └── services/
│       ├── file_parser.py      # PDF/DOCX/TXT/MD → plain text
│       ├── rag.py              # Chunk, embed, store, retrieve via ChromaDB
│       └── ollama_client.py    # Async streaming to Ollama
└── frontend/
    ├── Dockerfile              # Multi-stage: node build → nginx serve
    ├── nginx.conf              # SPA fallback + /api proxy + SSE support
    └── src/
        ├── App.tsx             # Two-column layout
        ├── api/client.ts       # Fetch wrapper + SSE stream reader
        └── components/
            ├── ChatWindow.tsx  # Message list + input
            ├── MessageBubble.tsx
            ├── FileUpload.tsx  # Drag-drop upload
            └── DocumentList.tsx
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload a file (multipart) |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/{id}` | Delete a document |
| POST | `/api/chat` | Chat with SSE streaming response |

## Verification Checklist

- [ ] `docker compose up --build` — all 4 containers start without errors
- [ ] `curl http://localhost` — returns the React app
- [ ] `curl http://localhost/api/documents` — returns `[]`
- [ ] Upload a PDF via the web UI — document appears in sidebar
- [ ] Check document, ask a question — streaming tokens render in real time
- [ ] Uncheck document — follow-up chat returns general (no context) answer
- [ ] Delete document — removed from sidebar + ChromaDB chunks purged
- [ ] `docker compose down && docker compose up` — model is NOT re-downloaded
- [ ] CPU-only host — chat works without GPU (slower but functional)
