# Local LLM Chat with File Attachments

A self-hosted AI chat application that runs a Qwen model entirely on-device, lets you upload documents (PDF, DOCX, TXT, MD) and ask questions about them using RAG (Retrieval-Augmented Generation).

## Architecture

```
Docker Compose
├── Ollama          (LLM inference — qwen2.5:7b)
├── ChromaDB        (vector store for document chunks)
├── Backend         (FastAPI — chat, upload, RAG orchestration)
└── Frontend        (React + Vite + Tailwind — served by Nginx)
```

All inter-service traffic stays on the internal Docker network. Only port **80** is exposed to the host.

## Quick Start

```bash
docker compose up --build
```

Then open [http://localhost](http://localhost) in your browser.

On first run, Ollama will pull the `qwen2.5:7b` model (~4.7 GB). Subsequent starts use the cached volume.

## Swap Model

Change the `MODEL_NAME` environment variable in `docker-compose.yml` — no code changes needed:

```yaml
environment:
  MODEL_NAME: qwen3:8b   # or any Ollama-supported model
```

## GPU Support

Uncomment the `deploy` block in the `ollama` service in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
```

Falls back to CPU automatically when not present.

## Project Structure

```
├── docker-compose.yml          # Orchestrates all 4 services
├── ollama/
│   └── entrypoint.sh           # Starts Ollama + pulls model on first run
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
