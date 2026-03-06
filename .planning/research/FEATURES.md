# Feature Landscape: Log Redaction / PII Sanitization

**Domain:** Multi-page developer utility with log redaction tool  
**Researched:** 2026-03-06  
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Text input** (upload file and/or paste) | Every redaction tool accepts input; paste is universal, upload supports larger files | LOW | Both are standard; paste-only is common (OpenRedaction playground, LogShield STDIN). Upload + paste = broader appeal. |
| **Pattern-based PII detection** (regex) | Industry standard for emails, IPs, SSNs, credit cards—fast, transparent, auditable | MEDIUM | 70+ to 500+ patterns in ecosystem. Regex is table stakes; LLM is additive. |
| **Deterministic output** | Same input → same output. Required for CI/CD, testing, and auditability | LOW | LogShield, PII-Shield, Maskify, OpenRedaction all emphasize this. No randomness. |
| **Structure preservation** | Format, whitespace, line breaks stay intact; only values replaced | LOW | LogShield, PII-Shield explicitly guarantee this. Essential for diff/audit. |
| **Download redacted output** | User needs to save/share the sanitized file | LOW | Non-negotiable. File or copy-to-clipboard are both acceptable. |
| **Local processing** | No data leaves machine—critical for log data and compliance | LOW | OpenRedaction, LogShield, PII-Shield are local-first. Cloud APIs are a different product. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Hybrid regex + LLM** for ambiguous PII | Regex misses hostnames, usernames in paths, contextual identifiers. LLM catches these while regex handles structured patterns | HIGH | OpenRedaction offers optional AI-assist; most tools are regex-only. LLM is best-effort—document limitations. |
| **Preview with highlights** before download | User can verify redactions before committing; reduces anxiety and mistakes | MEDIUM | Common in PDF/document redaction; less common in log tools. LogLayer, RedactionAPI don't emphasize this. |
| **IP-specific rules** (private untouched, allowlist, replacement pool) | Prevents over-redaction of internal IPs and test GeoIPs; domain-specific for Elastic ecosystem | MEDIUM | Private IP allowlist is rare; elastic-package GeoIP list is niche. Strong differentiator for target audience. |
| **Consistent replacement mapping** | Same PII → same dummy (e.g., host-001, host-002). Preserves traceability and log coherence | MEDIUM | PII-Shield uses HMAC for deterministic hashes; Presidio/Gretel use pseudonymization. Improves usability vs. generic [REDACTED]. |
| **Multi-page navigation** | Extensible for future tools; keeps app organized as scope grows | LOW | Standard UX; differentiator only if others are single-page. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Cloud/remote LLM** | Broader model access, no local setup | Data leaves machine; compliance risk; latency; cost | Local Ollama—project constraint is correct. |
| **Real-time log streaming** (tail -f integration) | “Live” redaction as logs flow | Adds complexity, different architecture; file-based redaction is sufficient for dev use | Batch upload/paste; keep it simple. |
| **Over-aggressive regex without allowlist** | “Safer” by redacting more | False positives; broken logs; unusable output | IP allowlist, whitelist for known-safe patterns (PII-Shield, Logfire callback). |
| **LLM-only detection** | Simpler than hybrid | LLMs are probabilistic, inconsistent; hard to audit; hallucination risk | Regex-first, LLM for ambiguous only. |
| **Generic [REDACTED] for everything** | Easy to implement | Loses correlation; “User X did Y” becomes “[REDACTED] did [REDACTED]” | Consistent replacement mapping (host-001, user-002). |
| **User authentication** | Multi-user, access control | Local dev tool; YAGNI; adds infra | Out of scope per PROJECT.md. |

## Feature Dependencies

```
Text input (upload + paste)
    └──requires──> Redaction engine (regex + optional LLM)
                       └──requires──> PII detection + replacement logic
                       └──requires──> IP rules (private, allowlist, replacement pool)
                       └──requires──> Consistent replacement mapping
    └──produces──> Redacted output

Preview with highlights
    └──requires──> Redacted output + diff/mapping data
    └──enhances──> Download (user confirms before saving)

Download
    └──requires──> Redacted output
```

### Dependency Notes

- **Preview requires redaction output:** Needs both final text and mapping of original→replacement to highlight changes.
- **Consistent replacement mapping requires detection:** Must collect all PII in a pass, build map, then replace in second pass (or single pass with lookahead).
- **IP rules depend on IP detection:** Regex finds IPs first; then apply private/allowlist/replacement logic.
- **LLM enhances regex:** Run regex first; LLM fills gaps for ambiguous tokens. Merge spans, dedupe, then redact.

## MVP Definition

### Launch With (v1)

Minimum viable product—what's needed to validate the concept.

- [ ] **Upload + paste input** — Both are expected; paste covers quick tests, upload covers files.
- [ ] **Regex for obvious PII** — Emails, public IPs (with private/allowlist rules), basic patterns.
- [ ] **IP handling** — Private IPs untouched; elastic GeoIP allowlist; public IPs replaced from allowlist.
- [ ] **Consistent replacement mapping** — Same PII → same dummy. Essential for log coherence.
- [ ] **Download redacted file** — Core output. Non-negotiable.
- [ ] **Multi-page navigation** — Chat + Redact Logs. Extensible for future tools.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **LLM for ambiguous PII** — Hostnames, usernames, paths with usernames. Hybrid approach.
- [ ] **Preview with highlights** — Verify before download. High user value, medium effort.
- [ ] **Broader file types** — .json, .csv, .yml, .conf beyond .log/.txt.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Custom regex patterns** — User-defined patterns. Adds config UI complexity.
- [ ] **Redaction summary/report** — Count of redactions by type. Nice for audit.
- [ ] **CI/CD integration** — `--fail-on-detect` style gate. Different use case (pipeline vs. interactive).

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Upload + paste input | HIGH | LOW | P1 |
| Regex PII detection | HIGH | MEDIUM | P1 |
| IP rules (private, allowlist, replacement) | HIGH | MEDIUM | P1 |
| Consistent replacement mapping | HIGH | MEDIUM | P1 |
| Download redacted file | HIGH | LOW | P1 |
| Multi-page navigation | HIGH | LOW | P1 |
| Preview with highlights | MEDIUM | MEDIUM | P2 |
| LLM for ambiguous PII | HIGH | HIGH | P2 |
| Broader file types | MEDIUM | LOW | P2 |
| Custom patterns | LOW | MEDIUM | P3 |
| Redaction summary | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch  
- P2: Should have, add when possible  
- P3: Nice to have, future consideration  

## Competitor Feature Analysis

| Feature | LogShield | OpenRedaction | PII-Shield | Our Approach |
|---------|-----------|---------------|------------|--------------|
| Input | STDIN (pipe) | Playground paste, npm lib | STDIN (sidecar) | Upload + paste (web UI) |
| Detection | Regex only | Regex + optional AI | Entropy + patterns | Hybrid regex + LLM |
| Deterministic | Yes | Yes (regex), optional AI | Yes (HMAC) | Yes (consistent mapping) |
| IP handling | Generic | Generic | N/A | Private untouched, GeoIP allowlist |
| Preview | No | No (playground shows result) | No | Yes (highlights before download) |
| Local | Yes | Yes (self-host) | Yes | Yes (Ollama on host) |
| Consistent mapping | N/A | [REDACTED] | HMAC hash | host-001, user-002 style |

## Sources

- [LogShield](https://logshield.dev/) — Deterministic CLI log sanitization
- [OpenRedaction](https://openredaction.com/) — Regex-first, optional AI-assist PII redaction
- [PII-Shield](https://pii-shield.com/) — Sidecar with entropy + deterministic HMAC
- [Logfire scrubbing](https://logfire.pydantic.dev/docs/how-to-guides/scrubbing) — Pattern + callback for false positive control
- [Philterd: Why LLM for PII is bad](https://blog.philterd.ai/why-using-an-llm-to-identify-and-redact-pii-and-phi-is-a-bad-idea/) — LLM limitations
- [10 Common PII Redaction Mistakes](https://openredaction.com/blog/10-common-pii-redaction-mistakes) — Over-redaction, false positives
- [Elastic PII NER + regex](https://www.elastic.co/observability-labs/blog/pii-ner-regex-assess-redact-part-2) — Hybrid approach
- [Microsoft Presidio pseudonymization](https://microsoft.github.io/presidio/samples/python/pseudonymization/) — Consistent replacement mapping

---
*Feature research for: Sandbox multi-tool dev utility with log redaction*  
*Researched: 2026-03-06*
