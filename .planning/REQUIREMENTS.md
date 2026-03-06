# Requirements: Sandbox — Multi-Tool Dev Utility

**Defined:** 2026-03-06
**Core Value:** Developers can safely sanitize log files by removing PII using hybrid regex + LLM detection, all running locally

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Navigation

- [ ] **NAV-01**: User can navigate between Chat and Redact Logs pages via a persistent navigation element
- [x] **NAV-02**: Page navigation preserves existing Chat page state (documents, selections) when switching pages
- [ ] **NAV-03**: Navigation structure is extensible — adding a new page requires minimal changes (route + nav entry)

### Input

- [x] **INP-01**: User can upload any text-based file (.log, .txt, .json, .csv, .yml, .conf, etc.) for redaction
- [x] **INP-02**: User can paste log text directly into a text area for redaction

### Detection

- [x] **DET-01**: Regex detects structured PII patterns: email addresses, public IP addresses
- [x] **DET-02**: Private IPs (10.x.x.x, 172.16-31.x.x, 192.168.x.x) are left untouched during redaction
- [x] **DET-03**: IPs from elastic-package allowed GeoIP list are left untouched during redaction
- [x] **DET-04**: Public IPs not in the allowed list are replaced with IPs from the allowed GeoIP list
- [x] **DET-05**: LLM (via Ollama) detects ambiguous PII that regex cannot: hostnames, usernames, paths containing usernames
- [x] **DET-06**: Replacement mapping is consistent — same PII value always maps to the same dummy replacement throughout a file (e.g. host-001, user-002)

### Output

- [x] **OUT-01**: User sees a preview of the redacted output with changes visually highlighted before downloading
- [x] **OUT-02**: User can download the redacted file
- [x] **OUT-03**: User can copy redacted text to clipboard
- [x] **OUT-04**: User sees a redaction summary showing count of changes by PII type

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Detection Enhancements

- **DET-07**: User can define custom regex patterns for domain-specific PII
- **DET-08**: User can configure which PII types to detect (toggle emails, IPs, hostnames, etc.)

### Input Enhancements

- **INP-03**: User can upload multiple files at once for batch redaction

### Integration

- **INT-01**: CLI/API mode for CI/CD pipeline integration (fail-on-detect gate)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time log streaming (tail -f) | Adds complexity; file-based redaction is sufficient for dev use |
| Cloud/remote LLM providers | Everything runs locally via Ollama — project constraint |
| User authentication | Local dev tool, no multi-user concerns |
| Binary file support | Only text-based files |
| Mobile-responsive layout | Desktop dev tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 1 | Pending |
| NAV-02 | Phase 1 | Complete (01-01) |
| NAV-03 | Phase 1 | Pending |
| INP-01 | Phase 3 | Complete |
| INP-02 | Phase 3 | Complete |
| DET-01 | Phase 2 | Complete |
| DET-02 | Phase 2 | Complete |
| DET-03 | Phase 2 | Complete |
| DET-04 | Phase 2 | Complete |
| DET-05 | Phase 2 | Complete |
| DET-06 | Phase 2 | Complete |
| OUT-01 | Phase 3 | Complete |
| OUT-02 | Phase 3 | Complete |
| OUT-03 | Phase 3 | Complete |
| OUT-04 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-06 after roadmap traceability*
