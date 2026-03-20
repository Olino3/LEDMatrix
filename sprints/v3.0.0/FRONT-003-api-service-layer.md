# FRONT-003 — API Service Layer and SSE Client

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)
**Blocks:** [FRONT-004](FRONT-004-dashboard-module.md), [FRONT-005](FRONT-005-plugins-module.md), [FRONT-006](FRONT-006-settings-module.md), [FRONT-007](FRONT-007-logs-store-modules.md)

---

## Context

All feature modules need to communicate with the FastAPI backend at `/api/v3/`. Rather than scatter `HttpClient` calls throughout components, this ticket creates a centralized service layer with typed TypeScript interfaces matching the Pydantic response models, an SSE service for real-time streams, and proper error handling.

The backend provides:
- REST endpoints at `/api/v3/system/*`, `/api/v3/config/*`, `/api/v3/plugins/*`, `/api/v3/fonts/*`, `/api/v3/wifi/*`, `/api/v3/starlark/*`
- SSE streams at `/api/v3/stream/stats`, `/api/v3/stream/display`, `/api/v3/stream/logs`
- OpenAPI schema at `/docs` (can be used to verify TypeScript interfaces)

---

## Acceptance Criteria

- [ ] TypeScript interfaces exist for all API response types (matching Pydantic models)
- [ ] `ApiService` wraps `HttpClient` with base URL, error handling, and typed responses
- [ ] `SseService` wraps `EventSource` with auto-reconnect, typed events, and Observable streams
- [ ] `SystemService` provides methods for system status, health, version
- [ ] `PluginService` provides methods for plugin CRUD, toggle, config, store operations
- [ ] `ConfigService` provides methods for config get/update (main, schedule, secrets)
- [ ] All services are injectable via Angular DI (`providedIn: 'root'`)
- [ ] Error responses are parsed into a typed `ApiError` class

---

## Implementation Checklist

### 1. Create TypeScript interfaces

- [ ] Create `frontend/src/app/core/models/` directory
- [ ] `system.model.ts` -- `SystemStatus`, `SystemVersion`, `HealthResponse`
- [ ] `plugin.model.ts` -- `PluginInfo`, `PluginConfig`, `PluginToggleRequest`, `StorePlugin`
- [ ] `config.model.ts` -- `SystemConfig`, `ScheduleConfig`, `ConfigUpdateRequest`
- [ ] `common.model.ts` -- `SuccessResponse`, `ErrorResponse`, `PaginatedResponse`
- [ ] `stream.model.ts` -- `StatsEvent`, `DisplayEvent`, `LogEvent`

### 2. Create base API service

- [ ] Create `frontend/src/app/core/services/api.service.ts`
- [ ] Inject `HttpClient`, use `environment.apiBase` for base URL
- [ ] Generic `get<T>()`, `post<T>()`, `put<T>()`, `delete<T>()` methods with typed returns
- [ ] Error interceptor that maps HTTP errors to `ApiError` instances
- [ ] Include `X-Request-ID` header on all requests (UUID)

### 3. Create SSE service

- [ ] Create `frontend/src/app/core/services/sse.service.ts`
- [ ] `connect(endpoint: string): Observable<T>` -- creates EventSource, wraps in Observable
- [ ] Auto-reconnect with exponential backoff on connection loss
- [ ] `statsStream$`, `displayStream$`, `logStream$` as lazy-initialized Observables
- [ ] Clean up EventSource on unsubscribe

### 4. Create domain services

- [ ] `system.service.ts` -- `getStatus()`, `getHealth()`, `getVersion()`, `performAction(action)`
- [ ] `plugin.service.ts` -- `list()`, `get(id)`, `getConfig(id)`, `updateConfig(id, config)`, `toggle(id, enabled)`, `install(id)`, `uninstall(id)`, `getStorePlugins()`
- [ ] `config.service.ts` -- `getMainConfig()`, `updateMainConfig(config)`, `getSchedule()`, `updateSchedule(schedule)`

### 5. Add HTTP interceptor for error handling

- [ ] Create `frontend/src/app/core/interceptors/error.interceptor.ts`
- [ ] Log errors to console in development
- [ ] Convert 4xx/5xx responses to typed `ApiError`
- [ ] Register interceptor in `app.config.ts`

### 6. Commit

```bash
git add frontend/src/app/core/
git commit -m "feat(frontend): add typed API service layer and SSE client"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Core service files exist
test -f frontend/src/app/core/services/api.service.ts && echo "OK: api service"
test -f frontend/src/app/core/services/sse.service.ts && echo "OK: sse service"
test -f frontend/src/app/core/services/system.service.ts && echo "OK: system service"
test -f frontend/src/app/core/services/plugin.service.ts && echo "OK: plugin service"
test -f frontend/src/app/core/services/config.service.ts && echo "OK: config service"

# 2. Model files exist
test -f frontend/src/app/core/models/system.model.ts && echo "OK: system models"
test -f frontend/src/app/core/models/plugin.model.ts && echo "OK: plugin models"
test -f frontend/src/app/core/models/common.model.ts && echo "OK: common models"
test -f frontend/src/app/core/models/stream.model.ts && echo "OK: stream models"

# 3. Build succeeds
cd frontend && npx ng build && echo "OK: build with services"

# 4. Interceptor registered
grep -q "error.interceptor" frontend/src/app/app.config.ts && echo "OK: interceptor registered"
```

---

## Notes

- TypeScript interfaces should mirror the Pydantic models in `src/api/models/`. When in doubt, check the OpenAPI schema at `/docs`.
- The SSE service uses native `EventSource`, NOT a WebSocket library. The backend uses `sse-starlette`.
- For the display preview stream, the backend sends base64-encoded PNG images. The SSE service should expose these as `Observable<string>` (base64 data URLs).
- Do NOT add WebSocket support in this ticket. The ROADMAP mentions WebSocket for display preview, but the current backend only supports SSE. WebSocket can be a future enhancement.
- All services use `providedIn: 'root'` for tree-shakeable singleton injection.
