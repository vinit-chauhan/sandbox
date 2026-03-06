# Roadmap: Sandbox — Multi-Tool Dev Utility

## Overview

Add multi-page navigation and a log redaction tool to the existing RAG chat app. Phases: (1) routing and nav with state preservation, (2) backend redaction pipeline (regex + GeoIP + LLM), (3) frontend upload/paste, preview with highlights, download, copy, and summary. All processing runs locally via Ollama.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Multi-Page Navigation** - Routing, layout, nav between Chat and Redact Logs; state preservation; extensible structure
- [x] **Phase 2: Redaction Backend** - FastAPI redaction API with regex + LLM, IP rules, GeoIP allowlist, consistent mapping (completed 2026-03-06)
- [x] **Phase 3: Redaction Frontend** - Upload, paste, preview with highlights, download, copy, redaction summary (completed 2026-03-06)

## Phase Details

### Phase 1: Multi-Page Navigation
**Goal**: Users can navigate between Chat and Redact Logs pages with state preserved and structure extensible for future tools
**Depends on**: Nothing (first phase)
**Requirements**: NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. User sees persistent navigation element with Chat and Redact Logs links
  2. User can switch between pages and see correct content for each
  3. Chat page state (documents, selections) persists when navigating away and back
  4. Navigation structure is extensible — adding a new tool page requires minimal changes (route + nav entry)
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — ChatContext and state lift (NAV-02)
- [x] 01-02-PLAN.md — Routing and navigation (NAV-01, NAV-03)

### Phase 2: Redaction Backend
**Goal**: Backend correctly redacts PII using hybrid regex + LLM with IP allowlist rules and consistent replacement mapping
**Depends on**: Nothing (can run parallel to Phase 1)
**Requirements**: DET-01, DET-02, DET-03, DET-04, DET-05, DET-06
**Success Criteria** (what must be TRUE):
  1. API redacts email addresses and non-allowed public IPs from input (regex)
  2. API leaves private IPs (10.x, 172.16–31.x, 192.168.x) unchanged
  3. API leaves IPs from elastic-package GeoIP list unchanged; replaces other public IPs with IPs from that list
  4. API redacts hostnames and usernames in paths via LLM with consistent mapping (same value → same replacement)
  5. Same PII value always maps to same dummy replacement throughout entire response
**Plans:** 4/4 plans complete

Plans:
- [x] 02-01-PLAN.md — GeoIP + Schemas + Test scaffolding (DET-03, DET-04)
- [x] 02-02-PLAN.md — Regex detection service (DET-01, DET-02, DET-03, DET-04, DET-06)
- [x] 02-03-PLAN.md — Ollama chat + LLM service (DET-05)
- [x] 02-04-PLAN.md — Redaction router + pipeline (integration)

### Phase 3: Redaction Frontend
**Goal**: Users can provide log input, see redacted preview with highlights, and obtain output (download, copy, summary)
**Depends on**: Phase 1, Phase 2
**Requirements**: INP-01, INP-02, OUT-01, OUT-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. User can upload text-based files (.log, .txt, .json, .csv, .yml, .conf, etc.) for redaction
  2. User can paste log text directly into a text area for redaction
  3. User sees preview of redacted output with changes visually highlighted before downloading
  4. User can download the redacted file
  5. User can copy redacted text to clipboard and see redaction summary (count by PII type)
**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — streamRedact API + Clean Logs terminology (foundation)
- [x] 03-02-PLAN.md — RedactPage full UI (input, preview, toolbar, summary)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Multi-Page Navigation | 2/2 | Complete | 01-01, 01-02 |
| 2. Redaction Backend | 4/4 | Complete   | 2026-03-06 |
| 3. Redaction Frontend | 2/2 | Complete   | 2026-03-06 |
