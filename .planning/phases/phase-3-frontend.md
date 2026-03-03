# Phase 3 — Frontend: React + Vite + Tailwind + Nginx

**Goal**: Browser UI lets users upload files, manage documents, and chat with real-time streaming responses.

**Depends on**: Phase 2 (backend API functional)

---

## Files to Create

- [ ] `frontend/Dockerfile` — multi-stage: `node:20-alpine` build → `nginx:alpine` serve
- [ ] `frontend/nginx.conf` — SPA fallback, `/api/` proxy to `backend:8000`, `proxy_buffering off` for SSE
- [ ] `frontend/package.json` — react, react-dom, vite, tailwindcss, typescript
- [ ] `frontend/vite.config.ts`
- [ ] `frontend/tailwind.config.ts`
- [ ] `frontend/index.html`
- [ ] `frontend/src/main.tsx`
- [ ] `frontend/src/App.tsx` — two-column layout; state: `docs[]`, `checkedIds[]`
- [ ] `frontend/src/api/client.ts` — `uploadFile`, `getDocuments`, `deleteDocument`, `streamChat`
- [ ] `frontend/src/components/FileUpload.tsx`
- [ ] `frontend/src/components/DocumentList.tsx`
- [ ] `frontend/src/components/ChatWindow.tsx`
- [ ] `frontend/src/components/MessageBubble.tsx`

---

## nginx.conf (critical for SSE)

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

---

## Component Hierarchy

```
App.tsx                            state: docs[], checkedIds[]
├── FileUpload.tsx                 drag-drop + click; progress bar
│     onUploaded(doc) → adds to docs[]
├── DocumentList.tsx               checkbox per doc; delete button
│     checkedIds → passed to ChatWindow
└── ChatWindow.tsx                 activeDocIds=checkedIds
      MessageBubble.tsx (×N)      user=right/blue, assistant=left/gray
```

---

## Component Details

### FileUpload.tsx
- Accepts: `.pdf`, `.docx`, `.txt`, `.md`
- Drag-and-drop (`onDragOver`, `onDrop`) + `<input type="file">` click
- Shows progress bar during upload
- Calls `onUploaded(doc)` on success

### DocumentList.tsx
- Checkbox list of uploaded docs; checked = active RAG context
- Delete button per doc → calls `deleteDocument(id)` + `onDeleted(id)`

### ChatWindow.tsx
- Scrollable `<MessageBubble>` list
- Typing indicator while model streams
- Textarea: send on `Ctrl+Enter` or Send button
- On submit:
  1. Append user message immediately
  2. Create empty assistant bubble
  3. `streamChat(req, token => append to last bubble)`

### MessageBubble.tsx
- `role=user`: right-aligned, blue background
- `role=assistant`: left-aligned, gray background

---

## api/client.ts — SSE Stream Parsing

```typescript
// streamChat(req, onToken):
// POST /api/chat → ReadableStream
// Split on "\n\n", filter "data: " lines
// Skip "[DONE]" sentinel
// JSON.parse → call onToken(parsed.token)
```

---

## Success Criteria

- [ ] `curl http://localhost` → React app HTML
- [ ] Upload PDF via UI → document card appears in sidebar
- [ ] Check document, type question → tokens stream in real time into assistant bubble
- [ ] Uncheck document → next chat returns general (no RAG) answer
- [ ] Delete document → removed from sidebar
- [ ] Refresh page → document list re-fetched and persists
