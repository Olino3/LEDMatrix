# FRONT-003c — StarlarkService

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-003](FRONT-003-api-service-layer.md)

---

## Context

The plugins module (FRONT-005) may need a `StarlarkService` wrapping `/api/v3/starlark/*` endpoints if Starlark/Pixlet app management is exposed in the Angular UI. This was out of scope for FRONT-003 which focused on core services (system, plugin, config).

## Scope

- Create `frontend/src/app/core/services/starlark.service.ts`
- Create `frontend/src/app/core/models/starlark.model.ts`
- Methods: `getStatus()`, `listApps()`, `getApp()`, `uploadApp()`, `deleteApp()`, `getAppConfig()`, `updateAppConfig()`, `toggleApp()`, `renderApp()`, `browseRepository()`, `installFromRepo()`, `getCategories()`, `installPixlet()`
- Follow the same pattern as `SystemService` — inject `ApiService`, typed returns
- Add tests following existing `*.spec.ts` patterns
- Export from `core/index.ts`
