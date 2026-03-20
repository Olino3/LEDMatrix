# SPIKE-005 — Starlark Configuration UI

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-006](FRONT-006-settings-module.md)
**Blocks:** _(none)_

---

## Context

The HTMX frontend had a Starlark configuration partial (`web_interface/templates/v3/partials/starlark_config.html`) for managing Starlark scripting configuration. The backend provides endpoints at `/api/v3/starlark/*`. This feature should be migrated to the Angular SPA.

---

## Acceptance Criteria

- [ ] Starlark config accessible from Settings page (as an additional tab) or as a standalone route
- [ ] Lists available Starlark scripts/configurations
- [ ] Allows editing Starlark script content
- [ ] Save/load operations via the Starlark API endpoints

---

## Implementation Checklist

### 1. Investigate backend endpoints

- [ ] Read `src/api/routers/starlark.py` to understand available endpoints and data models
- [ ] Determine what Starlark configuration the UI needs to expose

### 2. Create Starlark config component

- [ ] Create component in `frontend/src/app/features/settings/starlark/` or as a standalone route
- [ ] Implement UI based on discovered API capabilities
- [ ] Add code editor for Starlark script content (reuse from SPIKE-002 if applicable)

### 3. Commit

```bash
git add frontend/src/app/features/settings/starlark/
git commit -m "feat(frontend): add Starlark configuration UI"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Component exists
find frontend/src -name "*starlark*" -type f | head -1 && echo "OK: starlark component"

# 2. Build succeeds
cd frontend && npx ng build && echo "OK: build with starlark config"
```

---

## Notes

- Starlark is a niche feature. If the Starlark backend endpoints are minimal or unused, this ticket can be deprioritized.
- The code editor from SPIKE-002 (Raw JSON editor) may be reusable here for script editing.
- If Starlark support is experimental, consider placing this behind a feature flag or "Advanced" section.
