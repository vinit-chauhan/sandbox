# Phase 2 — Backend: FastAPI + RAG Services

**Goal**: REST API handles file upload, document management, and streaming chat with RAG context injection.

**Depends on**: Phase 1 (Ollama + ChromaDB running)

---

## Files to Create

- [ ] `backend/Dockerfile` — `python:3.11-slim`, installs requirements, runs uvicorn on `:8000`
- [ ] `backend/requirements.txt`
- [ ] `backend/schemas.py` — Pydantic models: `Message`, `ChatRequest`, `DocumentInfo`
- [ ] `backend/main.py` — FastAPI app with CORS middleware; mounts routers
- [ ] `backend/services/file_parser.py` — `parse_file(path, ext) -> str`
- [ ] `backend/services/rag.py` — ChromaDB client; `add_document`, `query`, `delete_document`
- [ ] `backend/services/ollama_client.py` — async NDJSON stream → `AsyncGenerator[str, None]`
- [ ] `backend/routers/documents.py` — upload, list, delete endpoints
- [ ] `backend/routers/chat.py` — `POST /api/chat` → SSE `StreamingResponse`

---

## requirements.txt

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

---

## Implementation Order (dependency chain)

```
schemas.py
  └── file_parser.py
  └── rag.py              (chromadb + sentence-transformers)
  └── ollama_client.py
        ├── routers/documents.py   (uses file_parser + rag)
        └── routers/chat.py        (uses rag + ollama_client)
              └── main.py
```

---

## RAG Pipeline

| Step | Detail |
|------|--------|
| File parsing | PDF → pypdf, DOCX → python-docx, TXT/MD → built-in open() |
| Chunking | `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)` |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` (~80 MB, runs on CPU) |
| Storage | ChromaDB `"documents"` collection; chunk IDs = `{doc_id}_chunk_{i}` |
| Retrieval | `where={"doc_id": {"$in": doc_ids}}`, top-k=5 chunks |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Accept `UploadFile`; save → parse → embed; return `{id, name}` |
| GET | `/api/documents` | List files in `/app/uploads/`; return `[{id, name}]` |
| DELETE | `/api/documents/{doc_id}` | Delete from disk + ChromaDB |
| POST | `/api/chat` | Body: `ChatRequest`; return SSE `StreamingResponse` |

### Chat flow
```
1. If document_ids provided:
   a. rag.query(document_ids, message, top_k=5) → context string
   b. Build system message: "Answer using this context:\n\n{context}"
2. messages = [system?] + history + [{"role": "user", "content": message}]
3. ollama_client.stream_chat(messages, model) → token generator
4. StreamingResponse(media_type="text/event-stream")

SSE format:
  data: {"token": "hello"}\n\n
  data: [DONE]\n\n
```

---

## Success Criteria

- [ ] `curl http://localhost:8000/api/documents` → `[]`
- [ ] Upload a file → returns `{id, name}`
- [ ] `GET /api/documents` → lists uploaded files
- [ ] `POST /api/chat` with streaming → SSE tokens flow
- [ ] `DELETE /api/documents/{id}` → 200, file + ChromaDB chunks removed
