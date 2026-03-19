# BACK-004 — FastAPI Middleware Stack

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-001](BACK-001-fastapi-app-scaffold.md), [BACK-002](BACK-002-dependency-updates.md)
**Blocks:** [BACK-005](BACK-005-api-routes-system.md)

---

## Context

The Flask app has several middleware concerns scattered across `app.py`: security headers (`add_security_headers`), request timing (`before_request`/`after_request`), captive portal redirect, rate limiting (via `flask-limiter`), and caching headers. These need to be reimplemented as FastAPI middleware classes in `src/api/middleware/`.

The ROADMAP also specifies new middleware for this phase: CORS (for Angular frontend in Phase 3), request ID correlation, and optional API key authentication.

---

## Acceptance Criteria

- [ ] `src/api/middleware/` package contains separate middleware modules
- [ ] `SecurityHeadersMiddleware` adds X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- [ ] `RequestIdMiddleware` generates a UUID request ID and attaches it to response headers and request state
- [ ] `RequestTimingMiddleware` logs request duration (replaces Flask `before_request`/`after_request`)
- [ ] `CORSMiddleware` configured for `localhost:4200` (Angular dev) and configurable origins
- [ ] `CachingMiddleware` sets cache headers based on path (static, API, HTML)
- [ ] `CaptivePortalMiddleware` redirects to `/v3` when AP mode is active (preserves current behavior)
- [ ] Rate limiting configured via `slowapi` (FastAPI-compatible rate limiter)

---

## Implementation Checklist

### 1. Create `src/api/middleware/` package

- [ ] Create `src/api/middleware/__init__.py` with `register_middleware(app)` function
- [ ] Create `src/api/middleware/security.py` -- `SecurityHeadersMiddleware`
- [ ] Create `src/api/middleware/request_id.py` -- `RequestIdMiddleware`
- [ ] Create `src/api/middleware/timing.py` -- `RequestTimingMiddleware`
- [ ] Create `src/api/middleware/caching.py` -- `CachingMiddleware`
- [ ] Create `src/api/middleware/captive_portal.py` -- `CaptivePortalMiddleware`

### 2. Configure CORS

- [ ] Use FastAPI's built-in `CORSMiddleware` from `starlette.middleware.cors`
- [ ] Default allowed origins: `["http://localhost:4200", "http://localhost:5000"]`
- [ ] Make origins configurable via `AppSettings`

### 3. Configure rate limiting

- [ ] Add `slowapi` to `pyproject.toml` dependencies
- [ ] Create `src/api/middleware/rate_limit.py` with default `1000/minute` limit
- [ ] Apply stricter limits to SSE endpoints (20/minute, matching current Flask config)

### 4. Register all middleware in `src/api/main.py`

- [ ] Call `register_middleware(app)` in the app factory
- [ ] Middleware order: CORS first, then security, request ID, timing, caching, captive portal

### 5. Tests

- [ ] Test request ID is present in response headers
- [ ] Test security headers are set on all responses
- [ ] Test cache headers differ for `/static/`, `/api/v3/`, and HTML paths
- [ ] Test CORS headers for allowed and disallowed origins

### 6. Commit

```bash
git add src/api/middleware/ pyproject.toml uv.lock
git commit -m "feat(api): add middleware stack (CORS, security headers, request ID, timing)"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Middleware package exists
test -d src/api/middleware && echo "OK: middleware package"
ls src/api/middleware/*.py | wc -l  # Should be at least 7 files

# 2. Middleware is importable
python3 -c "
from src.api.middleware import register_middleware
from src.api.middleware.security import SecurityHeadersMiddleware
from src.api.middleware.request_id import RequestIdMiddleware
print('OK: middleware importable')
"

# 3. Run middleware tests
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_api_middleware.py -v --override-ini=\"addopts=\"'
```

---

## Notes

- `slowapi` is the FastAPI-compatible equivalent of `flask-limiter`. Both use the same underlying `limits` library.
- The captive portal middleware replicates `captive_portal_redirect()` from `app.py`. It checks AP mode via `WiFiManager` and redirects non-allowlisted paths.
- API key authentication middleware is scaffolded but disabled by default (configurable via `AppSettings.api_key`). JWT support is scaffolded as a placeholder -- full implementation is not in scope for this phase.
- The request ID middleware should store the ID in `request.state.request_id` so route handlers and logging can access it.
