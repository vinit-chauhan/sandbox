# Stack Research

**Domain:** Multi-page developer utility app — React SPA routing + Python log redaction pipeline (hybrid regex + LLM)
**Researched:** 2026-03-06
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| react-router-dom | ^7.13 | Client-side SPA routing | De facto standard for React routing; v7 is backward-compatible with v6 API; declarative mode with `BrowserRouter` drops into existing Vite apps without framework-mode migration. Active maintenance, 23K+ dependents. |
| ollama | ^0.6 | Python client for local LLM (Ollama) | Official SDK; supports async, structured outputs via `format` + Pydantic, and configurable host (host.docker.internal). Reuse existing Ollama infra; cleaner than raw httpx for batch PII detection. |
| ipaddress (stdlib) | — | CIDR matching for GeoIP allowlist | No extra dependency; `ip in ip_network` checks; handles IPv4/IPv6 in elastic-package list. Standard since Python 3.3. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | — | Regex for deterministic PII (IPs, emails) | Always — first pass before LLM; fast, no false positives for structured patterns. |
| pydantic | ^2.9 | Schema for Ollama structured output | When calling Ollama for PII detection — define `PIIResult` model, pass `model_json_schema()` to `format`, validate response. Already transitive via ollama. |
| httpx | ^0.27 | Fetch GeoIP allowlist from GitHub | Already in stack; use `GET https://raw.githubusercontent.com/elastic/elastic-package/main/internal/fields/_static/allowed_geo_ips.txt` — no API token for public repo; cache response (e.g., 24h) to avoid repeated fetches. |
| NavLink / Link | (react-router-dom) | Navigation UI | `NavLink` for active route styling in nav bar; `Link` for internal links. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Vite | Unchanged | No routing-specific config; SPA already served by nginx `try_files $uri /index.html`. |
| nginx | Unchanged | Already has SPA fallback — no changes for routing. |

## Installation

```bash
# Frontend — routing
cd frontend && npm install react-router-dom@^7.13

# Backend — Ollama SDK (optional; can keep raw httpx for redaction if preferred)
# If adopting ollama package for structured PII extraction:
pip install ollama>=0.6
# (httpx>=0.27, pydantic>=2.9 are transitive)
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| react-router-dom 7.x | React Router Framework mode | When building new full-stack app with loaders/SSR; overkill for adding 2–3 pages to existing SPA. |
| ollama package | Raw httpx (current) | Keep httpx if team prefers minimal deps; httpx works fine for `/api/chat` with `format: json`; ollama adds cleaner typed API + structured output helpers. |
| raw.githubusercontent.com | GitHub API | Use API + `Accept: application/vnd.github.raw+json` if rate limits matter or token already in use; raw URL is simpler for public static file. |
| ipaddress (stdlib) | netaddr, ipwhois | Avoid extra deps; stdlib covers CIDR membership; netaddr only if you need more exotic operations. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| React Router v4/v5 | Deprecated patterns; no `Routes`/`useRoutes`; poor TypeScript support. | react-router-dom ^7 (or ^6 if pinning) |
| Create React App | Unmaintained; slow builds. | Vite (already in use) |
| HashRouter | Ugly URLs (#/chat); not needed with nginx try_files. | BrowserRouter |
| Presidio / spaCy NER for PII | Adds heavy ML deps; project already uses Ollama for LLM — stick to regex + Ollama for hybrid. | Regex + Ollama structured output |
| Third-party PII SDKs (OpenRedaction, pii-shield) | Cloud/API or different backends; project requires local-only Ollama. | Custom pipeline: regex → Ollama |
| Requests (sync) | Backend uses async FastAPI; blocking calls hurt concurrency. | httpx (async) |

## Stack Patterns by Variant

**If staying with raw httpx for Ollama:**
- POST to `{OLLAMA_BASE_URL}/api/chat` with `stream: false`, `format: {...}` for PII detection.
- Parse JSON response manually; no `ollama` package.

**If GeoIP list is bundled at build time:**
- Download `allowed_geo_ips.txt` in CI or at container build; serve from filesystem. Use when you want zero runtime network calls.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| react-router-dom@^7 | React 18+, Vite 5 | Node 20 required by v7 |
| ollama@^0.6 | httpx>=0.27, pydantic>=2.9 | Already satisfied by backend stack |
| Python 3.11 | ipaddress (stdlib) | No extra deps |

## GeoIP Allowlist Source

- **URL:** `https://raw.githubusercontent.com/elastic/elastic-package/main/internal/fields/_static/allowed_geo_ips.txt`
- **Format:** One CIDR per line (IPv4 and IPv6, e.g. `1.128.0.0/11`, `2a02:cf40::/29`)
- **Usage:** Fetch at startup or on first request; parse with `ipaddress.ip_network()`; cache in memory (e.g. TTL 24h) to avoid repeated HTTP calls.
- **Confidence:** HIGH — URL verified, format confirmed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| React Router | HIGH | Official docs, v7.13.1 verified via npm; declarative mode matches existing Vite setup |
| Log redaction (regex + LLM) | HIGH | Ollama structured outputs doc; stdlib ipaddress; httpx already in use |
| GeoIP allowlist | HIGH | raw URL fetched; format verified; stdlib handles CIDR |

## Sources

- React Router: https://reactrouter.com/how-to/spa — SPA setup, v7.13.1 (npm verified)
- React Router: https://reactrouter.com/start/modes — Declarative vs Framework mode
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs — `format` + Pydantic
- ollama PyPI: https://pypi.org/project/ollama/ — v0.6.1, dependencies
- Python ipaddress: https://docs.python.org/3/library/ipaddress.html — CIDR membership
- GitHub raw content: raw.githubusercontent.com — no token for public repos; verified via fetch
- elastic-package allowed_geo_ips.txt — fetched and format confirmed

---
*Stack research for: Multi-page dev utility with log redaction*
*Researched: 2026-03-06*
