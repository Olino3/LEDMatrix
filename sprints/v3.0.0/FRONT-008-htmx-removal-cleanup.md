# FRONT-008 — HTMX Removal and Legacy Frontend Cleanup

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Chore
**Depends on:** [FRONT-004](FRONT-004-dashboard-module.md), [FRONT-005](FRONT-005-plugins-module.md), [FRONT-006](FRONT-006-settings-module.md), [FRONT-007](FRONT-007-logs-store-modules.md)
**Blocks:** _(none)_

---

## Context

Once all feature modules are implemented in Angular, the legacy Jinja2/HTMX frontend can be removed. This ticket deletes the old templates, static files, and the pages router, and updates FastAPI to serve only the Angular SPA.

Files to remove:
- `web_interface/templates/` -- all Jinja2 templates
- `web_interface/static/` -- all CSS, JS, images (HTMX, Alpine.js, Tailwind, app.js, etc.)
- `src/api/routers/pages.py` -- HTMX page routes
- HTMX/Alpine.js references in any remaining code

Files to preserve:
- `web_interface/cache.py` -- if still used by backend services
- `web_interface/__init__.py` -- if used as a Python package

---

## Acceptance Criteria

- [ ] `web_interface/templates/` directory is deleted
- [ ] `web_interface/static/` directory is deleted
- [ ] `src/api/routers/pages.py` is deleted
- [ ] `pages_router` removed from `src/api/main.py` router includes
- [ ] `/v3` route no longer serves HTMX content
- [ ] `GET /` redirects to Angular SPA (or serves `index.html`)
- [ ] `htmx`, `alpinejs`, and related JS libraries removed from the project
- [ ] `Jinja2` dependency removed from `pyproject.toml` if no longer used elsewhere

---

## Implementation Checklist

### 1. Verify Angular SPA is complete

- [ ] Confirm all 5 feature modules (Dashboard, Plugins, Settings, Logs, Store) are functional
- [ ] Run `ng build` to produce the production bundle
- [ ] Verify SPA serves correctly from FastAPI

### 2. Remove HTMX pages router

- [ ] Delete `src/api/routers/pages.py`
- [ ] Remove `pages_router` import and `app.include_router(pages_router)` from `src/api/main.py`
- [ ] Remove `"pages"` from `openapi_tags` in `src/api/main.py`

### 3. Delete legacy frontend files

- [ ] Delete `web_interface/templates/` directory entirely
- [ ] Delete `web_interface/static/` directory entirely
- [ ] Check if `web_interface/cache.py` is still imported elsewhere; if not, delete it too

### 4. Update FastAPI static file mounts

- [ ] Remove the `web_interface/static` mount from `src/api/main.py`
- [ ] Ensure the Angular SPA mount at `/` is the primary file server
- [ ] Update the root redirect: `GET /` serves `index.html` (Angular handles routing)

### 5. Clean up dependencies

- [ ] Check if `Jinja2` is still needed by any code (FastAPI uses it for `Jinja2Templates`)
- [ ] If Jinja2 is no longer needed, remove it from `pyproject.toml`
- [ ] Remove `python-multipart` only if no longer used by file upload routes (it likely IS still used)

### 6. Update tests

- [ ] Remove or update any tests that reference HTMX endpoints (`/v3/*`)
- [ ] Update any test fixtures that assume `web_interface/templates/` exists
- [ ] Ensure all remaining API tests still pass

### 7. Commit

```bash
git add -A
git commit -m "chore(frontend): remove HTMX templates and legacy static files"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Legacy directories are gone
test ! -d web_interface/templates && echo "OK: templates removed"
test ! -d web_interface/static && echo "OK: static removed"

# 2. Pages router is gone
test ! -f src/api/routers/pages.py && echo "OK: pages router removed"

# 3. No HTMX references remain
! grep -r "htmx" src/ frontend/ --include="*.py" --include="*.ts" && echo "OK: no htmx refs"

# 4. Angular SPA serves correctly
test -f frontend/dist/ledmatrix/browser/index.html && echo "OK: SPA bundle exists"

# 5. API still works (imports OK)
python3 -c "from src.api.main import app; print(f'Routes: {len(app.routes)}'); print('OK: app loads')"

# 6. Tests pass
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins'
```

---

## Notes

- This is a destructive operation. Ensure all Angular feature modules are complete and tested before executing this ticket.
- The `web_interface/` directory may still be needed as a Python package if other code imports from it. Check for imports before deleting `__init__.py`.
- The `web_interface_v2` compatibility shim (created in Phase 2, SPIKE-001) lives in `src/web_interface/` or `web_interface_v2.py` -- do NOT remove it. It is needed until Phase 9.
- If `Jinja2` is still used by any backend code (error pages, email templates, etc.), keep it as a dependency.
- The `Jinja2Templates` import in `src/api/` should be removed along with the pages router.
