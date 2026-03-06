# Architecture Research

**Domain:** Multi-page developer utility app with log redaction pipeline  
**Researched:** 2026-03-06  
**Confidence:** HIGH

## Integration with Existing Architecture

### System Overview (Before and After)

**Current (RAG Chat only):**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  App.tsx (single page)                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐                 │
│  │ FileUpload  │  │DocumentList │  │   ChatWindow     │                 │
│  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘                 │
│         │                │                   │                            │
│         └────────────────┴───────────────────┴──→ api/client.ts          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                         /api/* (Nginx proxy → backend:8000)
                                    │
┌───────────────────────────────────┴───────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────┤
│  routers/chat.py  routers/documents.py                                  │
│         │                    │                                           │
│         ▼                    ▼                                           │
│  services/rag.py  services/file_parser.py  services/ollama_client.py    │
│         │                    │                    │                      │
│         ▼                    │                    │                       │
│  ChromaDB                    └────────────────────┴──→ Ollama (host)     │
└─────────────────────────────────────────────────────────────────────────┘
```

**After (multi-page + redaction):**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite + React Router)                 │
├─────────────────────────────────────────────────────────────────────────┤
│  App.tsx (layout + <Outlet />)                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Layout: shared Nav + sidebar (context-aware)                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │ /           │  │ /chat               │  │ /redact                 │  │
│  │ (redirect)  │  │ ChatPage            │  │ RedactPage              │  │
│  └─────────────┘  │ (existing components│  │ FileUpload+Paste+Preview│  │
│                   │  FileUpload, etc.)  │  │ +DiffView+Download      │  │
│                   └──────────┬──────────┘  └────────────┬────────────┘  │
│                              │                          │               │
│                              └──────────────────────────┴──→ api/client │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                         /api/* (unchanged)
                                    │
┌───────────────────────────────────┴───────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────┤
│  routers/chat.py  routers/documents.py  routers/redaction.py  (NEW)     │
│         │                    │                    │                      │
│         ▼                    ▼                    ▼                      │
│  rag.py           file_parser.py        redaction_service.py (NEW)      │
│  ollama_client.py                       ├─ regex_pii.py (NEW)           │
│                                         ├─ ollama_client.py (REUSE)     │
│                                         └─ geoip_allowlist.py (NEW)     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

### Frontend Components

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **App** | Root layout, Router provider, Nav | Router, Layout |
| **Layout** | Shared shell (nav bar, optional sidebar) | Nav, Outlet |
| **Nav** | Page links (Chat, Redact Logs) | React Router `Link` |
| **ChatPage** | Renders existing chat flow | FileUpload, DocumentList, ChatWindow, client |
| **RedactPage** | Redaction UI | RedactUpload, RedactPaste, RedactPreview, client |
| **RedactUpload** | File drop/select for log files | client.redactFile() |
| **RedactPaste** | Textarea for pasted log content | client.redactText() |
| **RedactPreview** | Diff view (original vs redacted) | react-diff-viewer or similar |
| **api/client** | All backend calls | Routers only; no cross-page logic |

### Backend Components

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **redaction router** | POST /api/redact (file or JSON body), GET /api/redact/download | redaction_service |
| **redaction_service** | Orchestrates regex + LLM, maintains replacement map | regex_pii, ollama_client, geoip_allowlist |
| **regex_pii** | Pattern matching for IPs, emails; private IP skip; allowed GeoIP | — |
| **ollama_client** | LLM calls for ambiguous PII (hostnames, usernames) | Ollama on host |
| **geoip_allowlist** | Fetch/cache elastic-package allowed GeoIP list | HTTP or bundled file |

### Boundary Rules

- **Frontend ↔ Backend**: All communication via `/api/*`; no direct ChromaDB/Ollama from frontend.
- **Redaction ↔ Chat**: Share nothing beyond `ollama_client`; redaction does not use RAG or ChromaDB.
- **Layout ↔ Pages**: Layout owns nav; pages own page-specific state; no shared global store required.

## Data Flow

### Multi-Page Routing

```
User clicks Nav link
    → React Router updates URL
    → Outlet renders matched Route component (ChatPage | RedactPage)
    → Page components mount/unmount; state local to page
```

**Nginx compatibility:** Existing `try_files $uri /index.html` serves `index.html` for all paths; React Router's `BrowserRouter` handles client-side routing. No Nginx changes.

### Log Redaction Pipeline

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────────────────┐
│ User Action  │     │ Backend Router  │     │ Redaction Service            │
│ (upload/paste)│────▶│ POST /api/redact│────▶│ 1. Parse input (text/bytes)  │
└──────────────┘     └─────────────────┘     │ 2. Regex phase (IPs, emails) │
                                             │    - Skip private IPs       │
                                             │    - Replace public IPs     │
       │                                     │      from allowed GeoIP     │
       │                                     │ 3. LLM phase (hostnames,    │
       │                                     │    usernames in paths)      │
       │                                     │    - Consistent mapping     │
       │                                     │ 4. Return {original,       │
       │                                     │    redacted, mapping?}      │
       │                                     └─────────────┬───────────────┘
       │                                                   │
       ▼                                                   ▼
┌─────────────────────┐                         ┌──────────────────────────┐
│ RedactPreview       │←────────────────────────│ Frontend receives JSON   │
│ - Diff highlighting │                         │ - Renders side-by-side   │
│ - User approves     │                         │   or inline diff         │
└──────────┬──────────┘                         └──────────────────────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────┐
│ User clicks Download │────▶│ GET /api/redact │
└─────────────────────┘     │   /download?id=  │
                            │ or POST with     │
                            │ redacted content │
                            └─────────────────┘
```

**Flow details:**

1. **Upload path:** `RedactUpload` → `FormData` with file → `POST /api/redact` (multipart).
2. **Paste path:** `RedactPaste` → `{ "text": "..." }` → `POST /api/redact` (JSON).
3. **Response:** `{ "original": string, "redacted": string, "replacements"?: Record<string,string> }`.
4. **Preview:** `RedactPreview` receives both; uses diff library to show changes.
5. **Download:** Option A — return filename + session ID; `GET /api/redact/download/{id}` returns `FileResponse`. Option B — client sends redacted text in body; backend returns `StreamingResponse` with `Content-Disposition: attachment`.

**Stateless recommendation:** Prefer returning redacted content in the initial response; store in React state. Download = create Blob from redacted string and trigger `URL.createObjectURL` + `<a download>`. No server-side session storage needed for small files.

## Recommended Project Structure

### Frontend Changes

```
frontend/src/
├── App.tsx                 # Router setup, Layout wrapper
├── main.tsx                # Wrap with <BrowserRouter>
├── components/
│   ├── Layout.tsx          # Nav + Outlet (NEW)
│   ├── Nav.tsx             # Link to /chat, /redact (NEW)
│   ├── ChatWindow.tsx      # existing
│   ├── DocumentList.tsx    # existing
│   ├── FileUpload.tsx      # existing (Chat context)
│   └── redact/             # (NEW folder)
│       ├── RedactUpload.tsx
│       ├── RedactPaste.tsx
│       ├── RedactPreview.tsx
│       └── RedactPage.tsx
├── api/
│   └── client.ts           # Add redactFile, redactText, types
└── pages/                  # (optional — or keep in components)
    ├── ChatPage.tsx        # Current App content for /chat
    └── RedactPage.tsx      # Or in components/redact/
```

### Backend Changes

```
backend/
├── main.py                 # Add: include_router(redaction.router)
├── routers/
│   ├── chat.py             # unchanged
│   ├── documents.py        # unchanged
│   └── redaction.py        # NEW
├── services/
│   ├── file_parser.py      # unchanged
│   ├── rag.py              # unchanged
│   ├── ollama_client.py    # unchanged (reuse)
│   ├── redaction_service.py # NEW
│   ├── regex_pii.py        # NEW
│   └── geoip_allowlist.py  # NEW
└── schemas.py              # Add RedactRequest, RedactResponse
```

## Architectural Patterns

### Pattern 1: Layout + Outlet for Multi-Page

**What:** Wrap routes in a shared `Layout` with `Nav`; render page content via `<Outlet />`.

**When:** Multiple top-level pages with shared navigation.

**Trade-offs:** Simple; no need for nested route config initially. Keeps Chat and Redact as sibling routes.

```tsx
// App.tsx
<Routes>
  <Route path="/" element={<Layout />}>
    <Route index element={<Navigate to="/chat" replace />} />
    <Route path="chat" element={<ChatPage />} />
    <Route path="redact" element={<RedactPage />} />
  </Route>
</Routes>
```

### Pattern 2: Router–Service for Redaction

**What:** Router receives request; validates; delegates to `redaction_service`; returns structured response.

**When:** All FastAPI endpoints; keeps HTTP concerns separate from business logic.

**Trade-offs:** Matches existing `documents.py` and `chat.py` patterns. Service is testable without HTTP.

### Pattern 3: Hybrid Regex + LLM Pipeline

**What:** Two-phase redaction: (1) regex for deterministic patterns; (2) LLM for ambiguous PII. Use consistent replacement map across both phases.

**When:** PII types mix structured (IPs, emails) and unstructured (hostnames, paths).

**Trade-offs:** Regex is fast; LLM adds latency. Run regex first to shrink LLM input. Reuse `ollama_client.stream_chat` or add non-streaming `generate()` for batch.

### Pattern 4: Client-Side Download from Response

**What:** Store `redacted` string in React state after API response. Download = `Blob` + `URL.createObjectURL` + `<a download>`.

**When:** File size is manageable (e.g., &lt; 1MB); no need for server to store files.

**Trade-offs:** No server-side session; simpler. For very large files, consider `StreamingResponse` from backend.

## Build Order

| Phase | Deliverable | Depends On | Rationale |
|-------|-------------|------------|-----------|
| **1. Routing** | React Router, Layout, Nav, Chat/Redact route stubs | — | Foundation; no backend changes |
| **2. Redaction backend core** | `redaction.py` router, `redaction_service`, `regex_pii` | — | Can test via curl/Postman |
| **3. GeoIP + LLM phase** | `geoip_allowlist`, LLM integration in service | Phase 2 | Completes redaction logic |
| **4. Redaction frontend** | RedactUpload, RedactPaste, RedactPreview, client methods | Phase 1, 2 | Needs routing and API |
| **5. Download** | Download button + blob/download flow | Phase 4 | Small addition |

**Dependency graph:**

```
Phase 1 (Routing) ─────────────────────────────────┐
                                                    ├──▶ Phase 4 (Redaction UI)
Phase 2 (Redaction backend) ───▶ Phase 3 (GeoIP+LLM)┘
                                                    │
                                                    └──▶ Phase 5 (Download)
```

## Anti-Patterns

### Anti-Pattern 1: Mixing Redaction with RAG

**What people do:** Reuse RAG/ChromaDB for redaction or store redacted logs in ChromaDB.

**Why it's wrong:** Redaction is stateless transform; RAG is document indexing. Different lifecycles.

**Do this instead:** Keep `redaction_service` independent; no ChromaDB in redaction path.

### Anti-Pattern 2: Processing Redaction in the Browser

**What people do:** Run regex or client-side LLM for redaction.

**Why it's wrong:** PROJECT.md constrains LLM to backend; regex-only misses ambiguous PII.

**Do this instead:** All redaction logic in FastAPI; frontend only uploads, displays, downloads.

### Anti-Pattern 3: Global State for Redaction Result

**What people do:** Put redacted content in global store (Redux/Zustand) for cross-page reuse.

**Why it's wrong:** Redaction result is page-scoped; no other page needs it.

**Do this instead:** Keep `original` and `redacted` in `RedactPage` (or RedactPreview) local state.

## Integration Summary

| Concern | Integration Approach |
|---------|----------------------|
| **Routing** | Add React Router; Layout + Nav + Outlet; Nginx `try_files` already SPA-ready |
| **Redaction API** | New router under `/api`; same CORS/proxy as existing |
| **LLM** | Reuse `ollama_client`; add non-streaming call if needed for batch |
| **File I/O** | Same `UploadFile` pattern as documents; different handler path |
| **Diff UI** | Add `react-diff-viewer` or `react-diff-view`; render in RedactPreview |

## Sources

- React Router v6 docs: reactrouter.com
- FastAPI Request Files: fastapi.tiangolo.com/tutorial/request-files/
- FastAPI FileResponse/StreamingResponse for downloads
- react-diff-viewer, react-diff-view (npm)
- Existing: `.planning/codebase/ARCHITECTURE.md`, `PROJECT.md`

---
*Architecture research for: Multi-page dev utility with log redaction*  
*Researched: 2026-03-06*
