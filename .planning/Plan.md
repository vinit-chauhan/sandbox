# Plan: Local LLM Chat App with File Attachments (Docker Compose)

## Context

A self-hosted AI chat application that:
- Runs a Qwen model entirely on-device (no external API keys)
- Lets users upload files (PDF, DOCX, TXT, MD) and ask questions about them
- Provides a polished web interface accessible via browser
- Is fully containerized and started with a single `docker compose up`

> **Model note**: `qwen3.5:9b` does not exist as a released Ollama model tag.
> Closest available options:
> - `qwen2.5:7b` — stable, widely tested
> - `qwen3:8b` — Qwen3 8B (latest Qwen3 family)
>
> This plan uses `qwen2.5:7b` as the default. Change `MODEL_NAME` in `docker-compose.yml` to swap without code changes.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Docker Compose                         │
│                                                              │
│  ┌─────────────┐    ┌───────────────┐    ┌───────────────┐  │
│  │   Ollama    │    │    Backend    │    │   Frontend    │  │
│  │ port 11434  │◄───│   FastAPI     │◄───│  React + Vite │  │
│  │ qwen2.5:7b  │    │   port 8000   │    │  Nginx :80    │  │
│  └─────────────┘    └──────┬────────┘    └───────────────┘  │
│                            │                                 │
│                     ┌──────▼────────┐                        │
│                     │   ChromaDB    │                        │
│                     │   port 8000   │                        │
│                     └───────────────┘                        │
└──────────────────────────────────────────────────────────────┘

User Browser → frontend:80 (Nginx + React SPA)
                    ↓ /api/* reverse proxy
              backend:8000 (FastAPI + uvicorn)
                ↙                   ↘
  ollama:11434                 chromadb:8000
  (LLM inference)              (vector store)
```

**4 Docker Compose services, 3 named volumes, only port 80 exposed to host.**

---

## Services Summary

| Service    | Image/Base         | Internal Port | Role                                    |
|------------|--------------------|---------------|-----------------------------------------|
| `ollama`   | `ollama/ollama`    | 11434         | Serve Qwen model via HTTP REST API      |
| `chromadb` | `chromadb/chroma`  | 8000          | Vector store for document chunks        |
| `backend`  | `python:3.11-slim` | 8000          | FastAPI: chat, upload, RAG orchestration|
| `frontend` | `node:20-alpine`   | 80 (→ host)   | React SPA served by Nginx               |

---

## Directory Structure

```
sandbox/
├── docker-compose.yml
├── ollama/
│   └── entrypoint.sh              # starts ollama serve, pulls model on first run
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app: CORS middleware, router mounts
│   ├── schemas.py                 # Pydantic request/response models
│   ├── routers/
│   │   ├── chat.py                # POST /api/chat (SSE streaming)
│   │   └── documents.py           # POST /api/upload, GET /api/documents, DELETE /api/documents/{id}
│   └── services/
│       ├── ollama_client.py       # async httpx NDJSON streaming to Ollama
│       ├── rag.py                 # embed, chunk, store, retrieve via ChromaDB
│       └── file_parser.py         # PDF/DOCX/TXT/MD → plain text
└── frontend/
    ├── Dockerfile                 # node:20 build stage → nginx:alpine serve stage
    ├── nginx.conf                 # SPA fallback + /api proxy + SSE buffering disabled
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                # Two-column layout: sidebar + chat area
        ├── api/
        │   └── client.ts          # fetch wrapper + SSE stream reader
        └── components/
            ├── ChatWindow.tsx     # message list + textarea input bar
            ├── MessageBubble.tsx  # user (right, blue) / assistant (left, gray) styling
            ├── FileUpload.tsx     # drag-drop upload zone with progress bar
            └── DocumentList.tsx   # checkbox list; checked docs = active RAG context
```

---

## Implementation Plan

---

### Phase 1 — Docker Compose + Ollama

#### `docker-compose.yml`

```yaml
services:
  ollama:
    image: ollama/ollama
    entrypoint: ["/bin/sh", "/entrypoint.sh"]
    volumes:
      - ollama_data:/root/.ollama
      - ./ollama/entrypoint.sh:/entrypoint.sh:ro
    environment:
      MODEL_NAME: qwen2.5:7b
    # GPU (optional — uncomment for NVIDIA):
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           capabilities: [gpu]

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma

  backend:
    build: ./backend
    depends_on:
      - ollama
      - chromadb
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
      CHROMA_HOST: chromadb
      CHROMA_PORT: "8000"
      MODEL_NAME: qwen2.5:7b
    volumes:
      - uploads:/app/uploads

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "80:80"

volumes:
  ollama_data:
  chroma_data:
  uploads:
```

Only `frontend:80` is exposed to the host. All inter-service traffic is over the internal Compose network.

#### `ollama/entrypoint.sh`

```bash
#!/bin/sh
# Start Ollama server in background
ollama serve &
PID=$!

# Wait for server to initialize before pulling
sleep 8

# Pull model (no-op if already cached in ollama_data volume)
ollama pull "${MODEL_NAME:-qwen2.5:7b}"

# Hand off to the server process
wait $PID
```

Model weights are stored in the `ollama_data` volume — pulled once, persisted across `docker compose down/up`.

**GPU Support**: Add `deploy.resources.reservations.devices` with `driver: nvidia, capabilities: [gpu]` to the `ollama` service. Falls back to CPU automatically when not present.

---

### Phase 2 — Backend (FastAPI)

#### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `backend/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
chromadb==0.5.0
sentence-transformers==3.0.0
pypdf==4.3.0
python-docx==1.1.0
python-multipart==0.0.9
langchain-text-splitters==0.2.0
```

#### `backend/schemas.py`

```python
from pydantic import BaseModel
from typing import Optional

class Message(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[list[str]] = None
    history: list[Message] = []

class DocumentInfo(BaseModel):
    id: str
    name: str
```

#### `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, documents

app = FastAPI(title="Local LLM Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)
```

#### `backend/services/file_parser.py`

```
parse_file(path: str, extension: str) -> str
```

| Extension    | Library        | Method                               |
|--------------|----------------|--------------------------------------|
| `.pdf`       | `pypdf`        | `PdfReader` → concat all page text   |
| `.docx`      | `python-docx`  | Iterate `doc.paragraphs` → join text |
| `.txt`/`.md` | built-in       | `open(path).read()`                  |

#### `backend/services/rag.py`

- Connects via `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (CPU, ~80 MB)
- ChromaDB collection name: `"documents"`

**`add_document(doc_id: str, text: str) -> None`**
1. Split with `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)`
2. Embed each chunk using SentenceTransformer
3. Upsert into ChromaDB with metadata `{"doc_id": doc_id}` and IDs `f"{doc_id}_chunk_{i}"`

**`query(doc_ids: list[str], query_text: str, top_k: int = 5) -> str`**
1. Embed `query_text`
2. Query ChromaDB with `where={"doc_id": {"$in": doc_ids}}`
3. Return top-k chunk texts joined by `"\n\n---\n\n"` as context string

**`delete_document(doc_id: str) -> None`**
- Delete all chunks matching `where={"doc_id": doc_id}`

#### `backend/services/ollama_client.py`

```
async def stream_chat(messages: list[dict], model: str) -> AsyncGenerator[str, None]
```

- POST to `{OLLAMA_BASE_URL}/api/chat` with `{"model": model, "messages": messages, "stream": true}`
- Use `httpx.AsyncClient` with `stream=True`
- Parse NDJSON line-by-line
- Yield `chunk["message"]["content"]` tokens (skip empty strings)

#### `backend/routers/documents.py`

| Method | Path                      | Description                                                              |
|--------|---------------------------|--------------------------------------------------------------------------|
| POST   | `/api/upload`             | Accept `UploadFile`; save to `/app/uploads/`; parse; embed; return `{id, name}` |
| GET    | `/api/documents`          | List all files in `/app/uploads/`; return `[{id, name}]`                |
| DELETE | `/api/documents/{doc_id}` | Delete file from disk + call `rag.delete_document(doc_id)`               |

File ID = sanitized filename stem. Name = original filename.

#### `backend/routers/chat.py`

**`POST /api/chat`** — body: `ChatRequest`

```
Chat flow:
1. If document_ids provided:
   a. Call rag.query(document_ids, message, top_k=5)
   b. Build system message: "Answer using this context:\n\n{context}"
2. Assemble messages list:
   - [system message if context exists]
   - [history messages]
   - {"role": "user", "content": message}
3. Call ollama_client.stream_chat(messages, model)
4. Return StreamingResponse(media_type="text/event-stream")

SSE format per token:   data: {"token": "hello"}\n\n
SSE terminal event:     data: [DONE]\n\n
```

---

### Phase 3 — Frontend (React + Vite + Tailwind)

#### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

#### `frontend/nginx.conf`

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;     # SPA fallback
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;            # REQUIRED for SSE streaming
        chunked_transfer_encoding on;
    }
}
```

#### `frontend/src/api/client.ts`

```typescript
// Types
interface Doc { id: string; name: string; }
interface Message { role: "user" | "assistant"; content: string; }
interface ChatRequest { message: string; document_ids?: string[]; history: Message[]; }

// API functions
uploadFile(file: File): Promise<Doc>
  → POST /api/upload (multipart/form-data)

getDocuments(): Promise<Doc[]>
  → GET /api/documents

deleteDocument(id: string): Promise<void>
  → DELETE /api/documents/{id}

streamChat(req: ChatRequest, onToken: (token: string) => void): Promise<void>
  → POST /api/chat with JSON body
  → Read response as ReadableStream
  → Parse SSE lines starting with "data: "
  → Skip "[DONE]" sentinel
  → Parse JSON, call onToken(parsed.token) per event
```

#### Component Details

**`App.tsx`**
- Two-column layout (CSS grid or flexbox)
- Left sidebar: `<FileUpload>` stacked above `<DocumentList>`
- Right panel: `<ChatWindow activeDocIds={checkedIds}>`
- State: `docs: Doc[]`, `checkedIds: string[]`

**`FileUpload.tsx`**
- Drag-and-drop zone (`onDragOver`, `onDrop`) + click-to-browse (`<input type="file">`)
- Accepted types: `.pdf`, `.docx`, `.txt`, `.md`
- Shows upload progress bar while uploading
- On success: calls `onUploaded(doc)` callback to parent

**`DocumentList.tsx`**
- Checkbox list of uploaded documents
- Checked state determines `activeDocIds` passed to chat
- Delete button per document — calls `deleteDocument(id)` + `onDeleted(id)` callback

**`ChatWindow.tsx`**
- Scrollable message list (`<MessageBubble>` per message)
- Loading/typing indicator while model is streaming
- Textarea at bottom; sends on `Ctrl+Enter` or Send button click
- Shows attached doc count badge when documents are active
- On submit:
  1. Append user message to local state immediately
  2. Create empty assistant bubble
  3. Call `streamChat(req, token => append token to last bubble)`

**`MessageBubble.tsx`**
- `role === "user"`: right-aligned, blue background
- `role === "assistant"`: left-aligned, gray background
- Renders content as plain text (extend with `react-markdown` if desired)

---

### Phase 4 — Data Flow

#### Upload Flow

```
User drops file.pdf
  → FileUpload calls POST /api/upload (multipart)
  → backend saves file to /app/uploads/
  → file_parser.parse_file() → raw text string
  → RecursiveCharacterTextSplitter → N chunks (512 tokens, 64 overlap)
  → SentenceTransformer encodes each chunk
  → ChromaDB upserts chunks with {doc_id} metadata
  → returns {id, name} to frontend
  → DocumentList shows new entry
```

#### Chat Flow

```
User types "Summarize section 3" with doc selected
  → ChatWindow calls POST /api/chat
     { message, document_ids: ["file"], history: [...] }
  → backend: rag.query(doc_ids, message, top_k=5)
     → embed message → cosine similarity → top-5 chunks
  → system prompt: "Answer using this context:\n\n{chunks}"
  → messages = [system, ...history, user]
  → ollama_client.stream_chat() → POST to Ollama /api/chat
  → Ollama streams NDJSON tokens
  → backend wraps as SSE: data: {"token": "..."}\n\n
  → frontend SSE reader calls onToken(token)
  → React appends token to assistant bubble in real-time
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Model serving | Ollama | Simple setup, CPU+GPU support, REST API, volume caching |
| Embeddings | `all-MiniLM-L6-v2` (local) | No external API calls, ~80 MB, fast on CPU |
| Vector store | ChromaDB | Lightweight, Docker-native, no extra config |
| Backend | FastAPI + SSE | Native async, streaming-first, Pydantic validation |
| Frontend | React + Vite + Tailwind | Fast build, widely known, utility-first styling |
| File types | PDF, DOCX, TXT, MD | Covers common document formats |
| Port exposure | Only `:80` to host | Minimal attack surface |
| Chunking | 512 tokens, 64 overlap | Balances context density and retrieval precision |

---

## Critical Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates all 4 services, volumes, env vars |
| `ollama/entrypoint.sh` | Pulls model on first start; no-op on subsequent starts |
| `backend/services/rag.py` | Core RAG: chunk, embed, upsert, cosine-retrieve |
| `backend/services/ollama_client.py` | Async NDJSON SSE streaming from Ollama |
| `backend/routers/chat.py` | Chat endpoint: context injection + SSE response |
| `frontend/src/api/client.ts` | SSE stream parsing in the browser |
| `frontend/nginx.conf` | SPA routing + `/api` proxy + `proxy_buffering off` for SSE |

---

## Startup Sequence

```bash
docker compose up --build
```

1. `ollama` starts → `ollama serve` → pulls `qwen2.5:7b` (~4.7 GB, first run only)
2. `chromadb` starts → mounts `chroma_data` volume
3. `backend` starts → uvicorn on `:8000` (waits for ollama + chromadb via `depends_on`)
4. `frontend` builds React app → Nginx serves on `:80`
5. Visit `http://localhost` in browser

---

## Verification Checklist

1. `docker compose up --build` — all 4 containers start without error
2. `curl http://localhost` — returns React app HTML
3. `curl http://localhost/api/documents` — returns `[]`
4. Upload a PDF via web UI → document appears in sidebar list
5. Check document checkbox, type a question → streaming response renders token by token
6. `docker compose down && docker compose up` — model is NOT re-downloaded (volume persists)
7. CPU-only host: chat works without GPU (slower but functional)

---

## Open Questions / Out of Scope

| Topic | Status | Notes |
|-------|--------|-------|
| Authentication | Out of scope | No user auth. Add OAuth2/JWT if multi-user needed. |
| Chat history persistence | Out of scope | In-memory per session. Add PostgreSQL for persistence. |
| Model swapping | Supported | Change `MODEL_NAME` env var — no code changes needed. |
| File size limit | Configurable | Default 50 MB via FastAPI; adjust in `main.py`. |
| HTTPS / TLS | Out of scope | Add Caddy or Traefik service if needed. |
| Markdown rendering | Optional | `MessageBubble` renders plain text; add `react-markdown` to extend. |
