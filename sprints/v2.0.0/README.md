# Sprint v2.0.0 -- Backend Modernization

**Goal:** Replace the Flask web interface with FastAPI, introduce Pydantic settings and typed request/response models, and migrate SSE streaming to async generators.

**ROADMAP phase:** Phase 2

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [BACK-001](BACK-001-fastapi-app-scaffold.md) | FastAPI application scaffold | Done | -- |
| [BACK-002](BACK-002-dependency-updates.md) | Update dependencies for FastAPI stack | Done | BACK-001 |
| [BACK-003](BACK-003-pydantic-settings.md) | Pydantic settings and config models | Done | BACK-001 |
| [BACK-004](BACK-004-middleware-stack.md) | FastAPI middleware stack | Done | BACK-001, BACK-002 |
| [BACK-005](BACK-005-api-routes-system.md) | Migrate system and config API routes | Done | BACK-002, BACK-003, BACK-004 |
| [BACK-006](BACK-006-api-routes-plugins.md) | Migrate plugin API routes | In Progress | BACK-003, BACK-005 |
| [BACK-007](BACK-007-sse-migration.md) | Migrate SSE streaming endpoints | Done | BACK-005 |
| [BACK-008](BACK-008-flask-removal-cleanup.md) | Flask removal and cleanup | Blocked | BACK-005, BACK-006, BACK-007 |
| [SPIKE-001](SPIKE-001-web-interface-v2-shim.md) | Compatibility shim for `web_interface_v2` import | Blocked | BACK-008 |
| [SPIKE-002](SPIKE-002-pages-v3-transition.md) | HTMX pages transition to FastAPI | Blocked | BACK-008 |
| [SPIKE-003](SPIKE-003-openapi-schema-validation.md) | OpenAPI schema validation and documentation | Blocked | BACK-006, BACK-007 |
| [SPIKE-004](SPIKE-004-mypy-strict-api.md) | Enforce strict typing for `src/api/` | Blocked | BACK-006 |
| [SPIKE-005](SPIKE-005-update-ci-for-fastapi.md) | Update CI pipeline for FastAPI | Blocked | BACK-008 |
| [SPIKE-006](SPIKE-006-fastapi-rate-limiting.md) | FastAPI rate limiting via slowapi | Open | BACK-004, BACK-007 |

## Dependency Graph

```
BACK-001 (FastAPI scaffold) [Done]
  +-- BACK-002 (dependency updates) [Done]
  |     +-- BACK-004 (middleware stack) [Done]
  |     |     +-- BACK-005 (system/config routes) [Done]
  |     |     |     +-- BACK-006 (plugin routes) [In Progress]
  |     |     |     |     +-- BACK-008 (Flask removal) [Blocked]
  |     |     |     |     +-- SPIKE-003 (OpenAPI docs) [Blocked]
  |     |     |     |     +-- SPIKE-004 (mypy strict) [Blocked]
  |     |     |     +-- BACK-007 (SSE migration) [Done]
  |     |     |     |     +-- BACK-008 (Flask removal) [Blocked]
  |     |     |     |     +-- SPIKE-003 (OpenAPI docs) [Blocked]
  |     |     |     +-- BACK-008 (Flask removal) [Blocked]
  |     |     |           +-- SPIKE-001 (web_interface_v2 shim) [Blocked]
  |     |     |           +-- SPIKE-002 (HTMX pages transition) [Blocked]
  |     |     |           +-- SPIKE-005 (CI update) [Blocked]
  |     |     +-- SPIKE-006 (rate limiting) [Open -- unblocked]
  +-- BACK-003 (Pydantic settings) [Done]
        +-- BACK-005 (system/config routes) [Done]
        +-- BACK-006 (plugin routes) [In Progress]
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
- [x] All API route handlers use `async def`
- [x] Pydantic request/response models validate all API inputs and outputs
- [x] SSE streaming uses `sse-starlette` with async generators
- [x] OpenAPI docs available at `/docs` and `/redoc`
- [x] CORS middleware configured for Angular frontend origin
- [x] Request ID middleware attaches correlation IDs to all responses
- [ ] Flask, flask-wtf, and flask-limiter removed from dependencies
- [ ] `web_interface_v2` compatibility shim in place with deprecation warning
- [ ] `SHIMS.md` created documenting active compatibility shims
- [ ] `mypy src/api/` passes with `disallow_untyped_defs = true`
- [ ] All existing tests pass (updated to use `httpx` test client)
- [ ] CI pipeline updated and passing
- [x] Plugin config continues to be delivered as plain `dict` (no Pydantic model exposure to plugins)

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
