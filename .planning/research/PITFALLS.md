# Pitfalls Research

**Domain:** Multi-page developer utility app with hybrid regex+LLM log redaction
**Researched:** 2026-03-06
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Line-by-line LLM calls causing unacceptable latency

**What goes wrong:**
Redaction processes each log line through Ollama separately, resulting in minutes of waiting for a 500-line file. Ollama’s throughput (~41 TPS at peak on consumer hardware) makes naive per-line calls impractical.

**Why it happens:**
Developers assume “call LLM on each line” is a simple extension of single-line logic and don’t account for Ollama’s latency and limited throughput.

**How to avoid:**
- **Batch lines** into chunks (e.g., 10–50 lines per request) and ask the LLM to return structured spans/ranges.
- **Filter before LLM**: Only send lines that regex flags as potentially ambiguous (e.g., likely hostnames, paths with slashes).
- **Async + progress**: Return job ID and poll or use SSE; show progress (e.g., “Processing line 120/500”).

**Warning signs:**
- Test logs with 100+ lines take >30 seconds.
- No batching logic; each line triggers its own `requests.post()`.
- Frontend blocks with no progress indicator.

**Phase to address:** LLM detection phase / Redaction pipeline phase

---

### Pitfall 2: LLM false negatives treated as acceptable

**What goes wrong:**
An SSN, hostname, or email is not redacted; a user shares the log and leaks PII. LLMs are probabilistic and can miss PII depending on context and phrasing.

**Why it happens:**
Overconfidence in LLM recall; hybrid systems are designed to catch ambiguous PII, but developers trust the LLM instead of treating it as best-effort.

**How to avoid:**
- **Regex-first**: Use regex for all structured PII (IPs, emails, SSNs, credit cards). LLM only for ambiguous tokens (hostnames, usernames in paths).
- **Clear split**: Document and enforce which entity types use regex vs LLM. Never rely on LLM for deterministic patterns.
- **Human review cue**: Consider a “confidence” level for LLM detections and surface low-confidence spans for review (or over-redact when in doubt).

**Warning signs:**
- LLM used for emails or IPs instead of regex.
- No regression tests with known PII strings.
- Requirements say “LLM catches everything regex misses” without limits.

**Phase to address:** LLM detection phase, Regex pattern phase

---

### Pitfall 3: Regex IP classification (private vs public vs allowed) is wrong or brittle

**What goes wrong:**
- Private IPs (e.g., 10.0.0.1) are redacted when they should stay.
- Invalid “IPs” like `999.999.999.999` or `192.168.1.2555` are matched.
- 172.x.x.x is mishandled (only 172.16–172.31 are private; 172.32+ is public).
- GeoIP allowlist uses CIDR (e.g., `1.128.0.0/11`); regex cannot handle range membership.

**Why it happens:**
Regex like `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` doesn’t validate octets (0–255) and can’t represent CIDR ranges. Range checks are done with strings or incomplete patterns.

**How to avoid:**
- **Parse, then classify**: Use `ipaddress.ip_address()` and `ipaddress.ip_network()` in Python. Check `ip.is_private` for RFC1918; iterate CIDR list for allowlist membership.
- **Avoid regex for validation**: Regex can find candidates; validate with `ipaddress` before classifying or redacting.

**Warning signs:**
- Regex used for “is this IP private?” or “is this IP in allowlist?”
- No tests for 172.15.x.x, 172.32.x.x, or IPv6.
- GeoIP list treated as simple string matching.

**Phase to address:** Regex/IP classification phase, GeoIP allowlist phase

---

### Pitfall 4: Replacement mapping not shared across regex and LLM paths

**What goes wrong:**
Regex replaces `prod-db-01` with `host-001`, but the LLM path introduces `host-002` for the same hostname. Output is inconsistent and correlations break.

**Why it happens:**
Regex and LLM run as separate passes with separate maps, or the map is not passed into the LLM flow.

**How to avoid:**
- **Single mapping structure**: One dict (original → replacement) shared by both regex and LLM phases.
- **Order**: Run regex first, then LLM. LLM receives text with regex replacements already applied, and both phases write to the same mapping.
- **Deterministic keys**: Use normalized originals (e.g., lowercased hostnames) so `Prod-DB-01` and `prod-db-01` map to the same replacement.

**Warning signs:**
- Two different mapping dicts or classes.
- LLM and regex phases implemented in isolation without integration tests.
- Same PII appears as different dummies in the same file.

**Phase to address:** Replacement mapping phase, Redaction pipeline integration

---

### Pitfall 5: State loss when navigating between Chat and Redact Logs

**What goes wrong:**
User uploads documents, selects some, then navigates to Redact Logs and back. Document list is empty, selections are gone. Component unmounts and local state is lost.

**Why it happens:**
State (`docs`, `checkedIds`) lives in route components. React Router unmounts components on route change, so state is reinitialized.

**How to avoid:**
- **Lift state above routes**: Keep `docs` and `checkedIds` in `App` (or a provider) that wraps `<Routes>` and stays mounted.
- **Or external store**: Use Context, Zustand, or similar for cross-route state.
- **Avoid relying on `location.state`** for anything that must survive refresh.

**Warning signs:**
- `useState` for shared data inside route components.
- Navigation clears previously loaded data.
- “Works until I click away and come back.”

**Phase to address:** Routing phase, Layout/navigation phase

---

### Pitfall 6: GeoIP allowlist fetch/cache/format assumptions

**What goes wrong:**
- Fetch on every redaction; GitHub rate-limits or network errors block users.
- Caching without invalidation; upstream list changes and old data is used.
- Format mismatches: list uses CIDR (`1.128.0.0/11`); code assumes plain IPs or different file encoding.
- IPv6 entries (e.g., `2a02:cf40::/29`) ignored because only IPv4 is handled.

**Why it happens:**
Treating the allowlist as a one-time copy-paste instead of an external, evolving resource with a specific format.

**How to avoid:**
- **Cache with TTL**: Fetch once per session or daily; store in memory or a small cache file.
- **Validate format**: Parse each line as `ipaddress.ip_network()`; skip or log invalid lines.
- **Handle both IPv4 and IPv6**: Use `ipaddress` for both.
- **Fallback**: If fetch fails, use last known good cache or fail explicitly.

**Warning signs:**
- No caching; every request hits GitHub.
- Only IPv4 handling.
- No tests for malformed or empty list lines.

**Phase to address:** GeoIP allowlist phase, Redaction pipeline phase

---

### Pitfall 7: Regex–LLM ordering and overlap confusion

**What goes wrong:**
- LLM sees raw IPs and “redacts” them, then regex runs and produces conflicting replacements.
- Or regex replaces first occurrence of a hostname, LLM replaces a second with a different value.
- Over-redaction: both regex and LLM redact the same span, producing `[REDACTED][REDACTED]`.

**Why it happens:**
No clear pipeline: order of operations, handoff format, and span boundaries are undefined.

**How to avoid:**
- **Defined pipeline**: (1) Regex for structured PII; (2) LLM for remaining ambiguous spans. Single replacement map for both.
- **Span awareness**: LLM prompt specifies “do not redact IPs or emails; only hostnames, usernames, paths.” Regex handles its entities completely.
- **Single replacement pass**: Apply replacements in one pass over the text using merged spans to avoid double redaction.

**Warning signs:**
- No documented pipeline order.
- LLM prompt doesn’t exclude regex-handled entities.
- Duplicate or overlapping redaction markers in output.

**Phase to address:** Redaction pipeline integration, LLM detection phase

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` for IPs | Quick to write | False positives (999.999.999.999), wrong private-range handling | Never — use `ipaddress` |
| Call LLM per line, no batching | Simple control flow | Minutes per file, poor UX | Never for production |
| Hardcode GeoIP list in source | No fetch logic | Stale data, manual updates | Only for initial spike/prototype |
| Put docs/checkedIds in route component | Less prop drilling | State loss on navigation | Never for shared app state |
| Skip LLM for “simple” logs | Faster | Missed hostnames, usernames in paths | Only if regex coverage is proven |
| Single-threaded replacement map | No locking | Wrong results if parallelized later | OK for MVP; document as non-thread-safe |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ollama | Sync calls, no timeout | Async with timeout; handle model-unavailable; batch requests |
| GeoIP list (GitHub raw) | Fetch every request | Cache with TTL; graceful fallback on fetch failure |
| React Router | State in route components | State in parent layout or external store; routes are presentational |
| Vite build | All routes go to `/` for SPA | Ensure server serves `index.html` for all paths (history mode) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|-----|----------|------------|----------------|
| Per-line LLM calls | >1 min for 100 lines | Batch lines; filter before LLM | ~50+ lines |
| Replacement map as O(n) scan per replacement | Slow on large files | Use dict; O(1) lookup | ~1k+ unique PII values |
| GeoIP fetch on every redaction | Slow first load, rate limits | Cache in memory or file | 2nd+ request in same session |
| Full-file LLM prompt | Token limit, OOM | Chunk; stream or paginate | ~10k+ lines |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Relying on LLM for SSN/credit card | PII leakage, compliance failure | Regex/validators only for structured PII |
| LLM output used as replacement without validation | Hallucinated PII in output | Use fixed dummy pool (host-001, etc.); never echo LLM-suggested values |
| Logs sent to remote LLM | Data exfiltration | PROJECT constraint: Ollama local only — enforce in code review |
| Predictable replacement patterns (host-001, host-002) | Correlation attacks if attacker knows mapping | Acceptable for dev logs; document as non-adversarial use case |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Blocking UI during redaction | App appears frozen | Progress indicator; async job + polling or SSE |
| No preview before download | User can’t verify redaction | Highlighted diff preview as required step |
| Silent regex/LLM failures | Bad output without warning | Surface errors; show “N lines processed, M spans redacted” |
| Losing draft when navigating away | Work lost on accidental nav | Persist paste buffer in sessionStorage or warn before leave |

---

## "Looks Done But Isn't" Checklist

- [ ] **IP classification:** Regex-only — verify `ipaddress` used for private/public/allowlist
- [ ] **GeoIP list:** Assumes IPv4 only — verify IPv6 CIDRs (`2a02:cf40::/29`) handled
- [ ] **Consistent mapping:** Same hostname in one place — verify same value in multiple lines maps identically
- [ ] **Routing:** Nav works locally — verify `npm run build && preview` serves all routes
- [ ] **State:** Docs persist on nav — verify Chat → Redact Logs → Chat keeps docs/selection
- [ ] **Batch LLM:** Works for 10 lines — verify 200-line file completes in reasonable time (<2 min)
- [ ] **Pipeline order:** Regex then LLM — verify no double-redaction, no LLM handling IPs

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Line-by-line LLM | MEDIUM | Add batching; refactor to chunk API; add progress |
| Wrong IP classification | LOW | Replace regex with `ipaddress`; add regression tests |
| State loss on nav | LOW | Lift state to App or store; 1–2 hour refactor |
| Replacement map split | MEDIUM | Merge maps; single apply pass; integration tests |
| GeoIP fetch every request | LOW | Add in-memory cache with TTL |
| Regex false positives (999.999) | LOW | Add `ipaddress` validation gate; filter invalid matches |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Line-by-line LLM latency | LLM detection / Redaction pipeline | 200-line file completes in <2 min |
| LLM false negatives for structured PII | Regex pattern phase, LLM prompt design | Regex handles IPs/emails; LLM only ambiguous |
| Wrong IP classification | Regex/IP phase, GeoIP phase | Tests: 172.15, 172.32, 999.999, CIDR allowlist |
| Split replacement mapping | Replacement mapping phase | Same PII → same dummy in multi-occurrence test |
| State loss on navigation | Routing phase | Navigate away and back; state persists |
| GeoIP fetch/cache/format | GeoIP allowlist phase | Cache hit on 2nd request; IPv6 entry works |
| Regex–LLM ordering | Redaction pipeline integration | No double-redaction; LLM skips regex entities |

---

## Sources

- [PRvL: Quantifying Capabilities and Risks of LLMs for PII Redaction](https://arxiv.org/html/2508.05545v1) (2025)
- [Why Using an LLM to Redact PII and PHI is a Bad Idea](https://www.philterd.ai/blog/why-using-an-llm-to-redact-pii-and-phi-is-a-bad-idea/) — Philterd
- [An Evaluation Study of Hybrid Methods for Multilingual PII Detection](https://arxiv.org/html/2510.07551v1)
- [PII Detection: Why Regex Fails](https://www.protecto.ai/blog/why-regex-fails-pii-detection-in-unstructured-text/)
- [Microsoft Presidio pseudonymization — thread-safety](https://microsoft.github.io/presidio/samples/python/pseudonymization/)
- [Validating IPv4 with regex](https://stackoverflow.com/questions/5284147/validating-ipv4-addresses-with-regexp) — 999.999 false positives
- [React Router state loss on navigation](https://stackoverflow.com/questions/75949910/react-router-v6-10-changing-route-loses-state-of-previous-page)
- [Python ipaddress for CIDR membership](https://docs.python.org/3/library/ipaddress.html)
- [elastic-package allowed_geo_ips.txt](https://github.com/elastic/elastic-package/blob/main/internal/fields/_static/allowed_geo_ips.txt) — CIDR format, includes IPv6

---
*Pitfalls research for: Sandbox multi-tool dev utility — log redaction + multi-page routing*
*Researched: 2026-03-06*
