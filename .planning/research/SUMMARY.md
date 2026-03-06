# Project Research Summary

**Project:** Sandbox multi-tool developer utility
**Domain:** Multi-page React SPA + Python log redaction pipeline (hybrid regex + LLM)
**Researched:** 2026-03-06
**Confidence:** HIGH

## Executive Summary

This is a multi-page developer utility app that adds a log redaction tool to an existing RAG chat product. Experts build PII sanitization tools with a **regex-first, LLM-augmented** pipeline: deterministic patterns (emails, IPs, SSNs) via regex; ambiguous tokens (hostnames, usernames in paths) via local LLM. Local-only processing and consistent replacement mapping (same PII → same dummy) are non-negotiable for auditability and log coherence.

The recommended approach: **React Router v7** for multi-page navigation with existing Vite/nginx; **FastAPI** redaction router with a **regex + Ollama** service; **ipaddress** stdlib for IP classification (private vs public vs GeoIP allowlist); and **elastic-package** GeoIP list from GitHub (cached). Key risks: naive per-line LLM calls causing unacceptable latency; wrong IP classification when using regex instead of `ipaddress`; and split replacement maps between regex and LLM. Mitigate with batched LLM requests, `ipaddress.ip_address()`/`ip_network()` for validation, and a single shared replacement map across both phases.

## Key Findings

### Recommended Stack

(Summary from [STACK.md](.planning/research/STACK.md))

**Core technologies:**
- **react-router-dom ^7.13** — Client-side SPA routing — De facto standard; declarative mode with `BrowserRouter` fits existing Vite app; v7 backward-compatible with v6 API.
- **ollama ^0.6** — Python client for local LLM — Official SDK; async, structured outputs via `format` + Pydantic; cleaner than raw httpx for batch PII detection.
- **ipaddress** (stdlib) — CIDR matching for GeoIP allowlist — No extra dependency; `ip in ip_network` checks; handles IPv4/IPv6; use instead of regex for IP validation.
- **re** (stdlib) — Regex for deterministic PII (IPs, emails) — First pass before LLM; fast, auditable.
- **httpx** — Fetch GeoIP allowlist from GitHub — Use raw URL; cache (e.g., 24h) to avoid repeated fetches.

**Avoid:** React Router v4/v5; HashRouter; Presidio/spaCy for PII (use regex + Ollama); cloud LLM; sync `requests` in async FastAPI.

### Expected Features

(Summary from [FEATURES.md](.planning/research/FEATURES.md))

**Must have (table stakes):**
- Upload + paste input — Users expect both; paste for quick tests, upload for files.
- Pattern-based PII detection (regex) — Industry standard for emails, IPs, SSNs; fast, auditable.
- Deterministic output — Same input → same output; essential for CI/CD and audit.
- Structure preservation — Format, whitespace, line breaks intact; only values replaced.
- Download redacted output — Non-negotiable.
- Local processing — No data leaves machine; compliance-critical.

**Should have (competitive):**
- Hybrid regex + LLM for ambiguous PII — Differentiator; LLM catches hostnames, usernames in paths.
- Preview with highlights before download — Verify redactions; reduces mistakes.
- IP-specific rules (private untouched, GeoIP allowlist, replacement pool) — Prevents over-redaction; Elastic ecosystem niche.
- Consistent replacement mapping — Same PII → same dummy (host-001, host-002); preserves traceability.

**Defer (v2+):**
- Custom regex patterns — User-defined; adds config UI.
- Redaction summary/report — Nice for audit.
- CI/CD integration — Different use case; pipeline vs. interactive.

### Architecture Approach

(Summary from [ARCHITECTURE.md](.planning/research/ARCHITECTURE.md))

Layout + Outlet for multi-page; new `redaction` router and `redaction_service`; hybrid regex-then-LLM pipeline with single replacement map; client-side download from response (no server-side session for small files).

**Major components:**
1. **Frontend Layout + Nav** — Shared shell; `Link`/`NavLink` for Chat and Redact Logs; `Outlet` renders page content.
2. **RedactPage** — RedactUpload, RedactPaste, RedactPreview; local state for original/redacted.
3. **redaction router** — POST /api/redact (file or JSON), returns `{original, redacted, replacements?}`.
4. **redaction_service** — Orchestrates regex phase → LLM phase; single replacement map; geoip_allowlist + regex_pii + ollama_client (reuse).
5. **regex_pii** — Pattern matching; private IP skip; allowed GeoIP via `ipaddress.ip_network()`.
6. **geoip_allowlist** — Fetch/cache elastic-package list from GitHub; TTL cache.

**Boundary rules:** Redaction is independent of RAG/ChromaDB; all processing in backend; frontend only uploads, displays, downloads.

### Critical Pitfalls

(Top 5 from [PITFALLS.md](.planning/research/PITFALLS.md))

1. **Line-by-line LLM calls** — Batches of 10–50 lines; filter before LLM (only ambiguous spans); async + progress indicator; never per-line calls for production.
2. **LLM false negatives for structured PII** — Regex-first for IPs, emails, SSNs; LLM only for hostnames, usernames in paths; document split clearly.
3. **Wrong IP classification** — Use `ipaddress.ip_address()` and `ip_network()`; never regex for "is private?" or CIDR; handle 172.15 vs 172.32, IPv6.
4. **Split replacement mapping** — Single dict shared by regex and LLM; run regex first, then LLM; deterministic keys (e.g., lowercased hostnames).
5. **State loss on navigation** — Lift `docs`/`checkedIds` above routes (App or provider); don't keep shared state in route components.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Routing
**Rationale:** Foundation; no backend changes; enables multi-page layout and Nav.
**Delivers:** React Router, Layout, Nav, Chat/Redact route stubs; BrowserRouter in main.tsx.
**Addresses:** Multi-page navigation (table stakes).
**Avoids:** State loss on navigation — design state location in App/provider from the start.

### Phase 2: Redaction Backend Core
**Rationale:** Can be tested via curl/Postman; independent of frontend.
**Delivers:** `redaction.py` router, `redaction_service`, `regex_pii`; POST /api/redact; regex for IPs, emails; private IP skip; consistent replacement mapping.
**Uses:** `re`, `ipaddress`, Pydantic, httpx.
**Implements:** regex_pii (with ipaddress validation), redaction_service orchestration.
**Avoids:** Wrong IP classification — use ipaddress from day one; split replacement map — single dict in service.

### Phase 3: GeoIP Allowlist + LLM Phase
**Rationale:** Completes redaction logic; depends on Phase 2.
**Delivers:** `geoip_allowlist` (fetch + cache); CIDR allowlist from elastic-package; LLM integration for ambiguous PII; batched LLM calls.
**Uses:** ollama package, httpx for GeoIP fetch, ipaddress for CIDR membership.
**Avoids:** Line-by-line LLM — batch lines; GeoIP fetch every request — cache with TTL; regex–LLM ordering — regex first, then LLM with clear prompt.

### Phase 4: Redaction Frontend
**Rationale:** Needs routing and API; completes user-facing flow.
**Delivers:** RedactUpload, RedactPaste, RedactPreview (diff view); api client methods; local state for original/redacted.
**Uses:** react-diff-viewer or similar; existing api/client pattern.
**Avoids:** Global state for redaction — keep in page local state.

### Phase 5: Download
**Rationale:** Small addition; completes core flow.
**Delivers:** Download button; Blob + `URL.createObjectURL` + `<a download>`; stateless — no server-side session.
**Avoids:** Server-side file storage — client creates blob from response.

### Phase Ordering Rationale

- **Phase 1 first:** Routing enables Layout and Nav; no other work depends on it.
- **Phase 2 before 3:** Core regex pipeline must exist before GeoIP and LLM; shared replacement map built in Phase 2.
- **Phase 3 after 2:** GeoIP and LLM enhance the pipeline; require redaction_service and regex_pii.
- **Phase 4 after 1 and 2:** Frontend needs routes and working API; can start when Phase 2 is usable.
- **Phase 5 last:** Trivial once Phase 4 has redacted content in state.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (GeoIP + LLM):** Batch size tuning (10–50 lines); LLM prompt design for span extraction; progress/SSE UX if batching adds latency.

Phases with standard patterns (skip research-phase):
- **Phase 1:** React Router well-documented; Layout + Outlet is standard.
- **Phase 2:** Regex + ipaddress + FastAPI patterns are established.
- **Phase 4:** react-diff-viewer, FormData upload, JSON body — standard.
- **Phase 5:** Blob download — trivial.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official docs, npm/pypi verified; ipaddress stdlib; GeoIP URL verified |
| Features | HIGH | Multiple competitor sources; OpenRedaction, LogShield, PII-Shield align with findings |
| Architecture | HIGH | Matches existing codebase patterns; FastAPI Router–Service; Layout + Outlet standard |
| Pitfalls | HIGH | Peer-reviewed, Stack Overflow, Presidio docs; IPv4 regex false positives well-documented |

**Overall confidence:** HIGH

### Gaps to Address

- **LLM batch size:** Research says 10–50 lines; needs empirical tuning during Phase 3 for target hardware.
- **State persistence:** Whether Chat docs/selection must survive navigation is product decision; PITFALLS flags it — confirm with PROJECT.md or requirements.

## Sources

### Primary (HIGH confidence)
- React Router SPA/modes — reactrouter.com
- Ollama structured outputs — docs.ollama.com
- Python ipaddress — docs.python.org/3/library/ipaddress.html
- elastic-package allowed_geo_ips.txt — GitHub raw URL verified
- FastAPI Request Files / FileResponse — fastapi.tiangolo.com

### Secondary (MEDIUM confidence)
- LogShield, OpenRedaction, PII-Shield — competitor feature analysis
- Philterd: Why LLM for PII is bad — LLM limitations
- Presidio pseudonymization — consistent replacement mapping
- Stack Overflow: React Router state loss, IPv4 regex validation

### Tertiary (validation during implementation)
- PRvL: Quantifying Capabilities and Risks of LLMs for PII Redaction (2025)
- Hybrid methods for multilingual PII detection

---
*Research completed: 2026-03-06*
*Ready for roadmap: yes*
