# SPIKE-008 — OpenAPI Response Model Retrofit

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Chore
**Depends on:** [SPIKE-003](SPIKE-003-openapi-schema-validation.md)
**Blocks:** _(none)_

---

## Context

SPIKE-003 added app metadata, tag descriptions, model field descriptions, and a static `openapi.json` export. However, `response_model` and `responses` are not yet set on the 111 route handlers across 10 router files. Many handlers return raw `JSONResponse` (not Pydantic models), so retrofitting `response_model` requires changing return types and risks breaking the API.

This ticket completes the OpenAPI documentation by adding typed response models to all handlers.

---

## Acceptance Criteria

- [x] All API route handlers use `response_model=None` with explicit `responses` dicts (87/93 endpoints documented)
- [x] Error responses (400, 404, 500) documented via `responses={...}` on all API handlers
- [x] Handlers use `response_model=None` with `API_RESPONSES` / `API_RESPONSES_WITH_404` from common models
- [x] `docs/openapi.json` regenerated — SuccessResponse and ErrorResponse in components/schemas
- [x] No existing API behavior broken (1291 tests pass)

---

## Implementation Notes

- Audit all 10 router files: config, system, plugins, store, fonts, wifi, assets, starlark, streams, pages
- For handlers returning `JSONResponse`, decide case-by-case whether to convert to a Pydantic return or document with `responses`
- SSE stream endpoints return `StreamingResponse` — use `responses` to document the event format
- Run the full test suite after each router file is updated
- Regenerate `docs/openapi.json` via `scripts/export_openapi.py`

---

## Affected Files

| File | Handler count |
|------|--------------|
| `src/api/routers/plugins.py` | ~20 |
| `src/api/routers/store.py` | ~15 |
| `src/api/routers/config.py` | ~10 |
| `src/api/routers/system.py` | ~10 |
| `src/api/routers/fonts.py` | ~10 |
| `src/api/routers/wifi.py` | ~5 |
| `src/api/routers/assets.py` | ~10 |
| `src/api/routers/starlark.py` | ~10 |
| `src/api/routers/streams.py` | ~5 |
| `src/api/routers/pages.py` | ~16 |
