# Sprint v2.0.0 -- Backend Modernization

**Goal:** Replace the Flask web interface with FastAPI, introduce Pydantic settings and typed request/response models, and migrate SSE streaming to async generators.

**ROADMAP phase:** Phase 2

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [BACK-001](BACK-001-fastapi-app-scaffold.md) | FastAPI application scaffold | Open | -- |
| [BACK-002](BACK-002-dependency-updates.md) | Update dependencies for FastAPI stack | Open | BACK-001 |
| [BACK-003](BACK-003-pydantic-settings.md) | Pydantic settings and config models | Open | BACK-001 |
| [BACK-004](BACK-004-middleware-stack.md) | FastAPI middleware stack | Open | BACK-001, BACK-002 |
| [BACK-005](BACK-005-api-routes-system.md) | Migrate system and config API routes | Open | BACK-002, BACK-003, BACK-004 |
| [BACK-006](BACK-006-api-routes-plugins.md) | Migrate plugin API routes | Open | BACK-003, BACK-005 |
| [BACK-007](BACK-007-sse-migration.md) | Migrate SSE streaming endpoints | Open | BACK-005 |
| [BACK-008](BACK-008-flask-removal-cleanup.md) | Flask removal and cleanup | Open | BACK-005, BACK-006, BACK-007 |
| [SPIKE-001](SPIKE-001-web-interface-v2-shim.md) | Compatibility shim for `web_interface_v2` import | Open | BACK-008 |
| [SPIKE-002](SPIKE-002-pages-v3-transition.md) | HTMX pages transition to FastAPI | Open | BACK-008 |
| [SPIKE-003](SPIKE-003-openapi-schema-validation.md) | OpenAPI schema validation and documentation | Open | BACK-006, BACK-007 |
| [SPIKE-004](SPIKE-004-mypy-strict-api.md) | Enforce strict typing for `src/api/` | Open | BACK-006 |
| [SPIKE-005](SPIKE-005-update-ci-for-fastapi.md) | Update CI pipeline for FastAPI | Open | BACK-008 |

## Dependency Graph

```
BACK-001 (FastAPI scaffold)
  +-- BACK-002 (dependency updates)
  |     +-- BACK-004 (middleware stack)
  |     |     +-- BACK-005 (system/config routes)
  |     |           +-- BACK-006 (plugin routes)
  |     |           |     +-- BACK-008 (Flask removal)
  |     |           |     +-- SPIKE-003 (OpenAPI docs)
  |     |           |     +-- SPIKE-004 (mypy strict)
  |     |           +-- BACK-007 (SSE migration)
  |     |           |     +-- BACK-008 (Flask removal)
  |     |           |     +-- SPIKE-003 (OpenAPI docs)
  |     |           +-- BACK-008 (Flask removal)
  |     |                 +-- SPIKE-001 (web_interface_v2 shim)
  |     |                 +-- SPIKE-002 (HTMX pages transition)
  |     |                 +-- SPIKE-005 (CI update)
  +-- BACK-003 (Pydantic settings)
        +-- BACK-005 (system/config routes)
        +-- BACK-006 (plugin routes)
```

## Critical Path

The longest dependency chain is:

```
BACK-001 -> BACK-002 -> BACK-004 -> BACK-005 -> BACK-006 -> BACK-008 -> SPIKE-001
```

Work can be parallelized:
- BACK-003 (Pydantic models) can proceed alongside BACK-002 + BACK-004
- BACK-007 (SSE) can proceed alongside BACK-006 (both depend on BACK-005)
- SPIKE-003, SPIKE-004 can proceed alongside BACK-008

## Definition of Done (Phase 2)

- [ ] FastAPI application serves all endpoints previously handled by Flask
- [ ] All API route handlers use `async def`
- [ ] Pydantic request/response models validate all API inputs and outputs
- [ ] SSE streaming uses `sse-starlette` with async generators
- [ ] OpenAPI docs available at `/docs` and `/redoc`
- [ ] CORS middleware configured for Angular frontend origin
- [ ] Request ID middleware attaches correlation IDs to all responses
- [ ] Flask, flask-wtf, and flask-limiter removed from dependencies
- [ ] `web_interface_v2` compatibility shim in place with deprecation warning
- [ ] `SHIMS.md` created documenting active compatibility shims
- [ ] `mypy src/api/` passes with `disallow_untyped_defs = true`
- [ ] All existing tests pass (updated to use `httpx` test client)
- [ ] CI pipeline updated and passing
- [ ] Plugin config continues to be delivered as plain `dict` (no Pydantic model exposure to plugins)

## Architecture Notes

### New directory structure after Phase 2

```
src/api/
  __init__.py          # create_app() factory
  main.py              # FastAPI instance, lifespan handler
  config.py            # AppSettings (pydantic-settings)
  dependencies.py      # Shared Depends() factories
  start.py             # Entry point (replaces web_interface/start.py)
  models/
    __init__.py
    common.py          # SuccessResponse, ErrorResponse, PaginatedResponse
    config.py          # SystemConfigResponse, ConfigUpdateRequest, etc.
    plugin.py          # PluginInfo, PluginConfigResponse, etc.
    system.py          # SystemStatusResponse, HealthResponse, etc.
  middleware/
    __init__.py        # register_middleware()
    security.py        # SecurityHeadersMiddleware
    request_id.py      # RequestIdMiddleware
    timing.py          # RequestTimingMiddleware
    caching.py         # CachingMiddleware
    captive_portal.py  # CaptivePortalMiddleware
    rate_limit.py      # slowapi rate limiting
  routers/
    __init__.py
    config.py          # /api/v3/config/*
    system.py          # /api/v3/system/*, /api/v3/health, etc.
    plugins.py         # /api/v3/plugins/* (CRUD, health, metrics)
    store.py           # /api/v3/plugins/store/*, install, update, uninstall
    fonts.py           # /api/v3/fonts/*
    wifi.py            # /api/v3/wifi/*
    assets.py          # /api/v3/plugins/assets/*, calendar, of-the-day
    starlark.py        # /api/v3/starlark/*
    streams.py         # /api/v3/stream/* (SSE)
    pages.py           # /v3/* (HTMX templates, temporary)
  services/
    __init__.py
    api_counter.py     # increment_api_counter (replaces web_interface_v2)
```

### Files preserved from `web_interface/`

- `web_interface/static/` -- CSS, JS, images (until Phase 3)
- `web_interface/templates/` -- Jinja2 templates (until Phase 3)
- `web_interface/cache.py` -- in-memory cache (evaluate if still needed)

### Files deleted

- `web_interface/app.py` -- Flask application
- `web_interface/blueprints/api_v3.py` -- Flask API blueprint (7,979 LOC)
- `web_interface/blueprints/pages_v3.py` -- Flask pages blueprint (512 LOC)

### Plugin Impact

| Plugin | Import affected | Shim provided | Update phase |
|---|---|---|---|
| `ledmatrix-music` | `from web_interface_v2 import increment_api_counter` | Yes (SPIKE-001) | Phase 9 |
| `ledmatrix-weather` | `from web_interface_v2 import increment_api_counter` | Yes (SPIKE-001) | Phase 9 |
| `odds-ticker` | `from web_interface_v2 import increment_api_counter` | Yes (SPIKE-001) | Phase 9 |
| `youtube-stats` | `from web_interface_v2 import increment_api_counter` | Yes (SPIKE-001) | Phase 9 |
