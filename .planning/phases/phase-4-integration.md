# Phase 4 — Integration & End-to-End Verification

**Goal**: All services work together; full upload → chat → delete flow verified; resilience confirmed.

**Depends on**: Phases 1–3 complete

---

## Full Data Flow Reference

### Upload Flow
```
User drops file.pdf
  → FileUpload: POST /api/upload (multipart)
  → backend: save to /app/uploads/
  → file_parser.parse_file() → raw text
  → RecursiveCharacterTextSplitter → N chunks (512 tokens, 64 overlap)
  → SentenceTransformer: embed each chunk
  → ChromaDB: upsert chunks with {doc_id} metadata
  → return {id, name} to frontend
  → DocumentList: new entry appears
```

### Chat Flow (with document selected)
```
User types "Summarize section 3" with doc checked
  → ChatWindow: POST /api/chat
     { message, document_ids: ["file"], history: [...] }
  → backend: rag.query(doc_ids, message, top_k=5)
     → embed message → cosine similarity → top-5 chunks
  → system prompt: "Answer using this context:\n\n{chunks}"
  → messages = [system, ...history, user]
  → ollama_client.stream_chat() → POST Ollama /api/chat
  → Ollama streams NDJSON tokens
  → backend wraps as SSE: data: {"token": "..."}\n\n
  → frontend SSE reader: onToken(token)
  → React appends token to assistant bubble in real time
```

---

## Verification Checklist

- [ ] `docker compose up --build` — all 4 containers healthy, no exit codes
- [ ] `curl http://localhost` — returns React HTML
- [ ] `curl http://localhost/api/documents` — returns `[]`
- [ ] Upload PDF via web UI → document appears in sidebar
- [ ] Check document, ask a question → streaming tokens render in real time
- [ ] Uncheck document → follow-up chat returns general (no context) answer
- [ ] Delete document → removed from sidebar + ChromaDB chunks purged
- [ ] `docker compose down && docker compose up` — model **not** re-downloaded (volume cache)
- [ ] CPU-only host — chat works without GPU (slower but functional)

---

## Known Extensions (Out of Scope)

| Feature | What to add |
|---------|-------------|
| Authentication | OAuth2/JWT middleware in FastAPI |
| Chat history persistence | PostgreSQL + SQLAlchemy session store |
| HTTPS / TLS | Caddy or Traefik as an additional Compose service |
| Markdown rendering | `react-markdown` in `MessageBubble.tsx` |
| File size limit | Adjust `max_upload_size` in `main.py` (default: 50 MB) |
| Model swapping | Already supported: change `MODEL_NAME` env var |
