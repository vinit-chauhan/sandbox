# Local LLM Chat with File Attachments

A self-hosted AI chat application that runs a Qwen model entirely on-device, lets you upload documents (PDF, DOCX, TXT, MD) and ask questions about them using RAG (Retrieval-Augmented Generation).

## Architecture

```
Host Machine
└── Ollama            (LLM inference — native, uses Metal/GPU)

Docker Compose
├── ChromaDB          (vector store for document chunks)
├── Backend           (FastAPI — chat, upload, RAG orchestration)
└── Frontend          (React + Vite + Tailwind — served by Nginx)
```

Ollama runs natively on the host for full Metal/GPU acceleration. The Docker services reach it via `host.docker.internal`. Only port **80** is exposed to the host.

## Quick Start

1. **Install & start Ollama** on your host:

```bash
# macOS — https://ollama.com/download
# Pull the model you want:
ollama pull qwen3.5:4b
```

2. **Start the Docker services**:

```bash
docker compose up --build
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
