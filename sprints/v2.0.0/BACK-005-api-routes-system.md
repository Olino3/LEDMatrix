# BACK-005 — Migrate System and Config API Routes

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-002](BACK-002-dependency-updates.md), [BACK-003](BACK-003-pydantic-settings.md), [BACK-004](BACK-004-middleware-stack.md)
**Blocks:** [BACK-007](BACK-007-sse-migration.md), [BACK-008](BACK-008-flask-removal-cleanup.md)

---

## Context

The Flask blueprint `api_v3.py` (7,979 LOC) contains all API routes in a single file. This ticket migrates the **system and config** route group to FastAPI routers in `src/api/routers/`. These are the lower-risk, less complex endpoints that establish the migration pattern for subsequent tickets.

Routes in scope (from `api_v3.py`):
- `/config/main` (GET, POST)
- `/config/schedule` (GET, POST)
- `/config/dim-schedule` (GET, POST)
- `/config/secrets` (GET)
- `/config/raw/main` (POST)
- `/config/raw/secrets` (POST)
- `/system/status` (GET)
- `/system/version` (GET)
- `/system/action` (POST)
- `/health` (GET)
- `/logs` (GET)
- `/errors/summary` (GET)
- `/errors/plugin/<plugin_id>` (GET)
- `/errors/clear` (POST)

---

## Acceptance Criteria

- [ ] `src/api/routers/config.py` contains all `/config/*` endpoints as FastAPI route handlers
- [ ] `src/api/routers/system.py` contains `/system/*`, `/health`, `/logs`, `/errors/*` endpoints
- [ ] All handlers use `async def` (async-first)
- [ ] All handlers use Pydantic request/response models from BACK-003
- [ ] Dependency injection via `Depends()` for ConfigManager, PluginManager
- [ ] Error responses use `ErrorResponse` model with consistent schema
- [ ] Routes are mounted on the FastAPI app under `/api/v3/` prefix
- [ ] Existing Flask routes are NOT removed yet (coexistence)

---

## Implementation Checklist

### 1. Create router package

- [ ] Create `src/api/routers/__init__.py`
- [ ] Create `src/api/routers/config.py` with `router = APIRouter(prefix="/config", tags=["config"])`
- [ ] Create `src/api/routers/system.py` with `router = APIRouter(tags=["system"])`

### 2. Migrate config routes to `config.py`

- [ ] `GET /config/main` -- return full config as JSON (typed response)
- [ ] `POST /config/main` -- accept partial config update, use atomic save
- [ ] `GET /config/schedule` -- return schedule section
- [ ] `POST /config/schedule` -- update schedule, validate with Pydantic
- [ ] `GET /config/dim-schedule` -- return dim schedule
- [ ] `POST /config/dim-schedule` -- update dim schedule
- [ ] `GET /config/secrets` -- return secrets (redacted)
- [ ] `POST /config/raw/main` -- raw JSON config overwrite
- [ ] `POST /config/raw/secrets` -- raw JSON secrets overwrite

### 3. Migrate system routes to `system.py`

- [ ] `GET /system/status` -- system metrics (CPU, memory, temp, service status)
- [ ] `GET /system/version` -- version info
- [ ] `POST /system/action` -- restart/stop service actions
- [ ] `GET /health` -- health check endpoint
- [ ] `GET /logs` -- fetch recent logs
- [ ] `GET /errors/summary` -- error aggregator summary
- [ ] `GET /errors/plugin/{plugin_id}` -- plugin-specific errors
- [ ] `POST /errors/clear` -- clear error aggregator

### 4. Wire routers into the app

- [ ] Import and include routers in `src/api/main.py` under `/api/v3` prefix
- [ ] Verify OpenAPI schema includes all new endpoints at `/docs`

### 5. Tests

- [ ] Write tests using `httpx.AsyncClient` for each endpoint
- [ ] Test config GET returns valid JSON matching `SystemConfigResponse`
- [ ] Test config POST validates input and returns errors for invalid data
- [ ] Test health endpoint returns 200 with status field
- [ ] Test error responses follow `ErrorResponse` schema

### 6. Commit

```bash
git add src/api/routers/
git commit -m "feat(api): migrate system and config routes to FastAPI routers"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Router files exist
test -f src/api/routers/config.py && echo "OK: config router"
test -f src/api/routers/system.py && echo "OK: system router"

# 2. Routers are importable
python3 -c "
from src.api.routers.config import router as config_router
from src.api.routers.system import router as system_router
print(f'Config routes: {len(config_router.routes)}')
print(f'System routes: {len(system_router.routes)}')
print('OK: routers importable')
"

# 3. Run route tests
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_api_routes_system.py test/test_api_routes_config.py -v --override-ini=\"addopts=\"'
```

---

## Notes

- The Flask blueprint `api_v3.py` is NOT modified in this ticket. Both Flask and FastAPI routes coexist temporarily.
- The `_save_config_atomic()` helper from `api_v3.py` should be extracted into a shared utility or service class, not duplicated.
- The `_coerce_to_bool()` helper should be replaced with Pydantic field validators where applicable.
- System status uses `psutil` which may not be available in all environments -- handle `ImportError` gracefully as the Flask code does.
- The `_get_display_service_status()` helper calls `systemctl` -- use `asyncio.create_subprocess_exec` for the async version.
