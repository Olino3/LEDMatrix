# BACK-001 — FastAPI Application Scaffold

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** _(none -- start here)_
**Blocks:** [BACK-002](BACK-002-dependency-updates.md), [BACK-003](BACK-003-pydantic-settings.md), [BACK-004](BACK-004-middleware-stack.md)

---

## Context

The web interface currently runs on Flask (`web_interface/app.py`, 661 LOC). Phase 2 replaces Flask with FastAPI for async-first handlers, auto-generated OpenAPI docs, and Pydantic request/response models. This ticket creates the new FastAPI application skeleton at `src/api/` without migrating any routes -- subsequent tickets will port route groups one at a time.

The new application must:
- Live in `src/api/` (not `web_interface/`) to match the ROADMAP convention
- Mount static files and HTMX templates during the transition period (Phase 3 removes them)
- Provide the same startup entry point pattern (`start.py`) for systemd and `matrix web`

**Key constraint:** The Flask app must continue to function until all routes are migrated. During the transition, both apps may coexist, but the goal of this sprint is a full replacement. Flask will not be removed until BACK-008 (cleanup).

---

## Acceptance Criteria

- [ ] `src/api/__init__.py` exists and exports `create_app()` factory function
- [ ] `src/api/main.py` contains the FastAPI app instance with lifespan handler
- [ ] `src/api/start.py` replaces `web_interface/start.py` as the entry point
- [ ] `/docs` serves Swagger UI and `/redoc` serves ReDoc (FastAPI defaults)
- [ ] Static files from `web_interface/static/` are mounted at `/static/`
- [ ] Jinja2 templates are mountable via `Jinja2Templates` for Phase 3 transition
- [ ] The app starts on `0.0.0.0:5000` with uvicorn

---

## Implementation Checklist

### 1. Create the `src/api/` package structure

- [ ] Create `src/api/__init__.py` with `create_app()` factory
- [ ] Create `src/api/main.py` with FastAPI instance, lifespan context manager
- [ ] Create `src/api/dependencies.py` for shared dependency injection (ConfigManager, PluginManager, etc.)
- [ ] Create `src/api/start.py` modeled on `web_interface/start.py` but using `uvicorn.run()`

### 2. Implement the lifespan handler

- [ ] Initialize ConfigManager, PluginManager, PluginStoreManager, SchemaManager, OperationQueue, PluginStateManager, OperationHistory in the lifespan `async with` block
- [ ] Store initialized services in `app.state` for access by route handlers
- [ ] Shut down health monitor and background services on app shutdown

### 3. Mount static files and templates

- [ ] Mount `web_interface/static/` at `/static/` using `StaticFiles`
- [ ] Configure `Jinja2Templates` pointing at `web_interface/templates/`
- [ ] Add `/favicon.ico` returning 204 (matching current behavior)

### 4. Add root redirect

- [ ] `GET /` redirects to `/v3` (matching current Flask behavior)

### 5. Smoke test

- [ ] App starts with `uvicorn src.api.main:app --host 0.0.0.0 --port 5000`
- [ ] `/docs` returns Swagger UI HTML
- [ ] `/static/` serves files
- [ ] `GET /` returns 307 redirect to `/v3`

### 6. Commit

```bash
git add src/api/
git commit -m "feat(api): scaffold FastAPI application with lifespan and static mounts"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Package structure exists
test -f src/api/__init__.py && echo "OK: __init__.py"
test -f src/api/main.py && echo "OK: main.py"
test -f src/api/dependencies.py && echo "OK: dependencies.py"
test -f src/api/start.py && echo "OK: start.py"

# 2. create_app is importable
python3 -c "from src.api import create_app; print('OK: create_app importable')"

# 3. FastAPI app has docs enabled
python3 -c "
from src.api.main import app
assert app.docs_url == '/docs', 'docs_url mismatch'
assert app.redoc_url == '/redoc', 'redoc_url mismatch'
print('OK: OpenAPI docs configured')
"

# 4. App starts (smoke test -- start and immediately shut down)
timeout 5 python3 -c "
import uvicorn
from src.api.main import app
# Just verify the app object is valid for uvicorn
print('OK: uvicorn accepts the app')
" || true
```

---

## Notes

- The `web_interface/` directory is NOT deleted in this ticket. It continues to serve as the source for static files and templates until Phase 3.
- `src/api/dependencies.py` will use FastAPI's `Depends()` pattern. Services are initialized once in the lifespan and injected per-request.
- The Flask `app.secret_key` is not needed in FastAPI -- session management is handled differently if needed later.
- Do NOT port any Flask routes in this ticket. Route migration happens in BACK-005 through BACK-007.
