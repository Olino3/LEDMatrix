# BACK-006 — Migrate Plugin API Routes

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-003](BACK-003-pydantic-settings.md), [BACK-005](BACK-005-api-routes-system.md)
**Blocks:** [BACK-008](BACK-008-flask-removal-cleanup.md), [SPIKE-003](SPIKE-003-openapi-schema-validation.md), [SPIKE-004](SPIKE-004-mypy-strict-api.md)

---

## Context

The largest route group in the Flask blueprint is the plugin management API (~5,000 LOC in `api_v3.py`). This includes plugin CRUD, store operations, config management, health monitoring, asset uploads, font management, WiFi management, cache management, and Starlark app management. These routes need to be split across multiple focused FastAPI routers.

This is the largest single ticket in the sprint. Each router file should be under 500 LOC. If any router exceeds this, split further during implementation.

---

## Acceptance Criteria

- [x] `src/api/routers/plugins.py` -- plugin CRUD, toggle, state, health, metrics (~25 endpoints)
- [x] `src/api/routers/store.py` -- plugin store, install, update, uninstall (~10 endpoints)
- [x] `src/api/routers/fonts.py` -- font catalog, upload, preview, delete (~8 endpoints)
- [x] `src/api/routers/wifi.py` -- WiFi status, scan, connect, AP mode (~8 endpoints)
- [x] `src/api/routers/assets.py` -- plugin asset upload, delete, list, calendar credentials (~6 endpoints)
- [x] `src/api/routers/starlark.py` -- Starlark app management (~10 endpoints)
- [x] All handlers use `async def` and Pydantic request/response models
- [x] File uploads use FastAPI's `UploadFile` type
- [x] All routers mounted under `/api/v3/` prefix

---

## Implementation Checklist

### 1. Create plugin CRUD router (`plugins.py`)

- [ ] `GET /plugins/installed` -- list installed plugins with metadata
- [ ] `POST /plugins/toggle` -- enable/disable plugin
- [ ] `GET /plugins/config` -- get plugin config + schema
- [ ] `POST /plugins/config` -- update plugin config (the largest single handler, ~900 LOC in Flask -- consider extracting config update logic into a service class)
- [ ] `POST /plugins/config/reset` -- reset plugin config to defaults
- [ ] `GET /plugins/schema` -- get plugin config schema
- [ ] `POST /plugins/action` -- plugin-specific actions
- [ ] `GET /plugins/health` -- all plugin health
- [ ] `GET /plugins/health/{plugin_id}` -- single plugin health
- [ ] `POST /plugins/health/{plugin_id}/reset` -- reset health metrics
- [ ] `GET /plugins/metrics` -- all plugin metrics
- [ ] `GET /plugins/metrics/{plugin_id}` -- single plugin metrics
- [ ] `POST /plugins/metrics/{plugin_id}/reset` -- reset metrics
- [ ] `GET,POST /plugins/limits/{plugin_id}` -- get/set resource limits
- [ ] `GET /plugins/operation/{operation_id}` -- operation status
- [ ] `GET /plugins/operation/history` -- operation history
- [ ] `DELETE /plugins/operation/history` -- clear history
- [ ] `GET /plugins/state` -- plugin state snapshot
- [ ] `POST /plugins/state/reconcile` -- reconcile state
- [ ] `POST /plugins/authenticate/spotify` -- Spotify auth flow
- [ ] `POST /plugins/authenticate/ytm` -- YouTube Music auth flow

### 2. Create store router (`store.py`)

- [ ] `GET /plugins/store/list` -- list available plugins
- [ ] `GET /plugins/store/github-status` -- GitHub API rate limit status
- [ ] `POST /plugins/store/refresh` -- refresh plugin registry
- [ ] `POST /plugins/install` -- install from registry
- [ ] `POST /plugins/install-from-url` -- install from URL
- [ ] `POST /plugins/update` -- update plugin
- [ ] `POST /plugins/uninstall` -- uninstall plugin
- [ ] `POST /plugins/registry-from-url` -- add registry from URL
- [ ] `GET /plugins/saved-repositories` -- list saved repos
- [ ] `POST /plugins/saved-repositories` -- add saved repo
- [ ] `DELETE /plugins/saved-repositories` -- delete saved repo

### 3. Create fonts router (`fonts.py`)

- [ ] `GET /fonts/catalog` -- list available fonts
- [ ] `GET /fonts/tokens` -- font design tokens
- [ ] `GET,POST /fonts/overrides` -- font overrides
- [ ] `DELETE /fonts/overrides/{element_key}` -- delete override
- [ ] `POST /fonts/upload` -- upload font file
- [ ] `GET /fonts/preview` -- preview font rendering
- [ ] `DELETE /fonts/{font_family}` -- delete font

### 4. Create WiFi router (`wifi.py`)

- [ ] `GET /wifi/status` -- WiFi connection status
- [ ] `GET /wifi/scan` -- scan for networks
- [ ] `POST /wifi/connect` -- connect to network
- [ ] `POST /wifi/disconnect` -- disconnect
- [ ] `POST /wifi/ap/enable` -- enable AP mode
- [ ] `POST /wifi/ap/disable` -- disable AP mode
- [ ] `GET,POST /wifi/ap/auto-enable` -- auto-enable settings

### 5. Create assets router (`assets.py`)

- [ ] `POST /plugins/assets/upload` -- upload plugin asset
- [ ] `POST /plugins/assets/delete` -- delete plugin asset
- [ ] `GET /plugins/assets/list` -- list plugin assets
- [ ] `GET /plugins/{plugin_id}/static/{file_path}` -- serve plugin static files
- [ ] `POST /plugins/of-the-day/json/upload` -- upload JSON data
- [ ] `POST /plugins/of-the-day/json/delete` -- delete JSON data
- [ ] `POST /plugins/calendar/upload-credentials` -- upload Google Calendar credentials
- [ ] `GET /plugins/calendar/list-calendars` -- list Google calendars

### 6. Create Starlark router (`starlark.py`)

- [ ] `GET /starlark/status` -- Starlark runtime status
- [ ] `GET /starlark/apps` -- list Starlark apps
- [ ] `GET /starlark/apps/{app_id}` -- get app details
- [ ] `POST /starlark/upload` -- upload Starlark app
- [ ] `DELETE /starlark/apps/{app_id}` -- delete app
- [ ] `GET,PUT /starlark/apps/{app_id}/config` -- app config
- [ ] `POST /starlark/apps/{app_id}/toggle` -- toggle app
- [ ] `POST /starlark/apps/{app_id}/render` -- render app
- [ ] `GET /starlark/repository/browse` -- browse repository
- [ ] `POST /starlark/repository/install` -- install from repository
- [ ] `GET /starlark/repository/categories` -- list categories
- [ ] `POST /starlark/install-pixlet` -- install Pixlet runtime

### 7. Wire all routers into the app

- [ ] Include all routers in `src/api/main.py`
- [ ] Verify OpenAPI docs show all endpoints

### 8. Tests

- [ ] Write tests for plugin CRUD endpoints (list, toggle, config get/set)
- [ ] Write tests for store endpoints (list, install, uninstall)
- [ ] Write tests for font endpoints (catalog, upload)
- [ ] Test file upload endpoints with `UploadFile`
- [ ] Test error responses for invalid plugin IDs

### 9. Commit

```bash
git add src/api/routers/
git commit -m "feat(api): migrate plugin, store, font, wifi, asset, starlark routes to FastAPI"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. All router files exist
for f in plugins store fonts wifi assets starlark; do
  test -f "src/api/routers/${f}.py" && echo "OK: ${f}.py"
done

# 2. No single router exceeds 500 LOC
for f in src/api/routers/*.py; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 500 ]; then
    echo "WARNING: $f is $lines lines (target: <500)"
  else
    echo "OK: $f is $lines lines"
  fi
done

# 3. Routers are importable
python3 -c "
from src.api.routers.plugins import router as plugins_router
from src.api.routers.store import router as store_router
from src.api.routers.fonts import router as fonts_router
from src.api.routers.wifi import router as wifi_router
from src.api.routers.assets import router as assets_router
from src.api.routers.starlark import router as starlark_router
print('OK: all routers importable')
"

# 4. Run tests
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_api_routes_plugins.py test/test_api_routes_store.py -v --override-ini=\"addopts=\"'
```

---

## Notes

- The plugin config POST handler is ~900 LOC in Flask. Extract the config update logic into a service class (`src/api/services/plugin_config_service.py`) rather than keeping it all in the route handler.
- File upload endpoints should use FastAPI's `UploadFile` and `File()` dependencies instead of Flask's `request.files`.
- The `_get_plugin_version()` helper from `api_v3.py` should move to a shared utility.
- If any single router file exceeds 500 LOC during implementation, split it into sub-routers (e.g., `plugins_crud.py`, `plugins_health.py`).
- Plugin Impact: None. These are web API endpoints -- plugins do not import from `api_v3.py`.
