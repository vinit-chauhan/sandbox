# Phase 1 — Infrastructure: Docker Compose + Ollama

**Goal**: All four services start successfully; Ollama serves `qwen2.5:7b` via HTTP.

**Depends on**: Nothing (starting point)

---

## Files to Create

- [ ] `docker-compose.yml` — 4 services (`ollama`, `chromadb`, `backend`, `frontend`), 3 volumes, only port 80 exposed to host
- [ ] `ollama/entrypoint.sh` — starts `ollama serve`, waits 8s, pulls `${MODEL_NAME}` (no-op if already cached in volume)

---

## Key Decisions

- `MODEL_NAME=qwen2.5:7b` as default; swap via env var — no code changes needed
- GPU block present in compose but commented out; CPU fallback is automatic
- All inter-service traffic stays on the internal Compose network

---

## docker-compose.yml Outline

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

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma

  backend:
    build: ./backend
    depends_on: [ollama, chromadb]
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
      CHROMA_HOST: chromadb
      CHROMA_PORT: "8000"
      MODEL_NAME: qwen2.5:7b
    volumes:
      - uploads:/app/uploads

  frontend:
    build: ./frontend
    depends_on: [backend]
    ports:
      - "80:80"

volumes:
  ollama_data:
  chroma_data:
  uploads:
```

## ollama/entrypoint.sh Outline

```bash
#!/bin/sh
ollama serve &
PID=$!
sleep 8
ollama pull "${MODEL_NAME:-qwen2.5:7b}"
wait $PID
```

---

## Success Criteria

- [ ] `docker compose up --build` — all 4 containers start, no exit codes
- [ ] Ollama container logs show model ready
- [ ] `docker compose down && docker compose up` — model is **not** re-downloaded (volume cache hit)
