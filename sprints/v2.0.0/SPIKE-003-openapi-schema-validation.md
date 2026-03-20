# SPIKE-003 — OpenAPI Schema Validation and Documentation

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Chore
**Depends on:** [BACK-006](BACK-006-api-routes-plugins.md), [BACK-007](BACK-007-sse-migration.md)
**Blocks:** _(none)_

---

## Context

One of the key benefits of FastAPI is auto-generated OpenAPI documentation. After all routes are migrated (BACK-005 through BACK-007), this ticket validates the generated OpenAPI schema, ensures all endpoints have proper descriptions, and exports a static `openapi.json` for consumers.

---

## Acceptance Criteria

- [x] All API endpoints appear in the OpenAPI schema at `/docs`
- [x] Every endpoint has a summary and description
- [x] Request/response models have field descriptions and examples
- [x] `openapi.json` is exported to `docs/openapi.json` for reference
- [x] Tags group endpoints logically (config, system, plugins, store, fonts, wifi, streams, starlark, assets, pages)
- [ ] Error responses (400, 404, 422, 500) are documented in the schema — deferred to [SPIKE-008](SPIKE-008-openapi-response-models.md)

---

## Implementation Checklist

### 1. Add descriptions to all route handlers

- [ ] Review each router and add `summary` and `description` to `@router.get()` / `@router.post()` decorators
- [ ] Add `response_model` to all handlers that return JSON
- [ ] Add `responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}` to handlers that can fail

### 2. Add model field descriptions

- [ ] Add `Field(description="...")` to Pydantic model fields
- [ ] Add `model_config` with `json_schema_extra={"example": {...}}` for key models

### 3. Configure OpenAPI metadata

- [ ] Set `title="LEDMatrix API"`, `version="2.0.0"`, `description` in FastAPI constructor
- [ ] Add `license_info`, `contact` metadata
- [ ] Configure tag descriptions via `openapi_tags` parameter

### 4. Export static schema

- [ ] Create `scripts/export_openapi.py` that imports the app and writes `app.openapi()` to `docs/openapi.json`
- [ ] Run the script and commit the output

### 5. Verify completeness

- [ ] Count endpoints in OpenAPI schema vs. routes registered
- [ ] Ensure no endpoint is missing from the schema

### 6. Commit

```bash
git add src/api/ docs/openapi.json scripts/export_openapi.py
git commit -m "docs(api): add OpenAPI descriptions and export static schema"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. OpenAPI schema file exists
test -f docs/openapi.json && echo "OK: openapi.json exists"

# 2. Schema is valid JSON
python3 -c "
import json
with open('docs/openapi.json') as f:
    schema = json.load(f)
print(f'Paths: {len(schema[\"paths\"])}')
print(f'Tags: {[t[\"name\"] for t in schema.get(\"tags\", [])]}')
print('OK: valid OpenAPI schema')
"

# 3. All expected tags are present
python3 -c "
import json
with open('docs/openapi.json') as f:
    schema = json.load(f)
tags = {t['name'] for t in schema.get('tags', [])}
expected = {'config', 'system', 'plugins', 'store', 'fonts', 'wifi', 'streams', 'starlark', 'pages'}
missing = expected - tags
assert not missing, f'Missing tags: {missing}'
print('OK: all tags present')
"
```

---

## Notes

- The OpenAPI schema is a snapshot. It should be regenerated whenever routes change. Consider adding a CI step to verify the committed schema matches the runtime schema.
- SSE endpoints may not render perfectly in Swagger UI since they return streaming responses. Add a note in the description.
- The exported `openapi.json` will be useful for the Angular frontend in Phase 3 (code generation with `ng-openapi-gen` or similar).
