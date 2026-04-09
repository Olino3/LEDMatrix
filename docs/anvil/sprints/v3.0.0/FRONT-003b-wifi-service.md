# FRONT-003b — WifiService

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-003](FRONT-003-api-service-layer.md)

---

## Context

The settings module (FRONT-006) will need a `WifiService` wrapping `/api/v3/wifi/*` endpoints. This was out of scope for FRONT-003 which focused on core services (system, plugin, config).

## Scope

- Create `frontend/src/app/core/services/wifi.service.ts`
- Create `frontend/src/app/core/models/wifi.model.ts`
- Methods: `getStatus()`, `scan()`, `connect()`, `disconnect()`, `enableAP()`, `disableAP()`, `getAutoEnableAP()`, `setAutoEnableAP()`
- Follow the same pattern as `SystemService` — inject `ApiService`, typed returns
- Add tests following existing `*.spec.ts` patterns
- Export from `core/index.ts`
