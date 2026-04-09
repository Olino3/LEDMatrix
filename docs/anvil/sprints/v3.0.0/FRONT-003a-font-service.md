# FRONT-003a — FontService

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-003](FRONT-003-api-service-layer.md)

---

## Context

The settings module (FRONT-006) will need a `FontService` wrapping `/api/v3/fonts/*` endpoints. This was out of scope for FRONT-003 which focused on core services (system, plugin, config).

## Scope

- Create `frontend/src/app/core/services/font.service.ts`
- Create `frontend/src/app/core/models/font.model.ts`
- Methods: `getCatalog()`, `getTokens()`, `getOverrides()`, `updateOverrides()`, `deleteOverride()`, `uploadFont()`, `previewFont()`, `deleteFont()`
- Follow the same pattern as `SystemService` — inject `ApiService`, typed returns
- Add tests following existing `*.spec.ts` patterns
- Export from `core/index.ts`
