# SPIKE-002 — HTMX Pages Transition to FastAPI

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-008](BACK-008-flask-removal-cleanup.md)
**Blocks:** _(none -- end of chain)_

---

## Context

The Flask blueprint `pages_v3.py` (512 LOC) serves Jinja2 templates for the HTMX-based web interface. These pages render HTML partials for each section (overview, plugins, settings, logs, etc.). Per the ROADMAP, the HTMX templates are kept during Phase 2 and removed in Phase 3 (Angular SPA).

This ticket ports the `pages_v3.py` routes to a FastAPI router that continues to serve the same Jinja2 templates. This is a mechanical translation -- no template changes, no new UI features.

---

## Acceptance Criteria

- [x] `src/api/routers/pages.py` contains all routes from `pages_v3.py`
- [x] Jinja2 templates render correctly via FastAPI's `Jinja2Templates`
- [x] All HTMX partial routes (`/v3/partials/{partial_name}`) work
- [x] `GET /v3` renders the main `v3/index.html` template
- [x] Template context data is identical to what Flask provided
- [x] Flash messages: not needed — no `get_flashed_messages()` in any template; errors returned as HTML status 500
- [ ] Note: `weather.html` and `stocks.html` templates never existed — those partials return 500 (same as Flask behavior). Tracked in SPIKE-007.

---

## Implementation Checklist

### 1. Create `src/api/routers/pages.py`

- [ ] Create router with `APIRouter(prefix="/v3", tags=["pages"])`
- [ ] Configure `Jinja2Templates(directory="web_interface/templates")`

### 2. Migrate index route

- [ ] `GET /v3/` -- render `v3/index.html` with config data
- [ ] Load config via dependency-injected ConfigManager
- [ ] Pass same template context as Flask version (schedule_config, config JSON, paths)

### 3. Migrate partial routes

- [ ] `GET /v3/partials/{partial_name}` -- render the appropriate partial template
- [ ] Port all 14 partial loaders (overview, general, display, durations, schedule, weather, stocks, plugins, fonts, logs, raw-json, wifi, cache, operation-history)
- [ ] Each partial loader returns `HTMLResponse` via `templates.TemplateResponse`

### 4. Handle Flask-specific features

- [ ] Replace `flash()` messages with a client-side notification system (or pass errors as template context)
- [ ] Replace `url_for()` calls in templates with hardcoded paths or a custom template function
- [ ] Verify `redirect()` calls work with FastAPI's `RedirectResponse`

### 5. Tests

- [ ] Test `GET /v3/` returns 200 with HTML content
- [ ] Test `GET /v3/partials/overview` returns HTML
- [ ] Test unknown partial name returns 404

### 6. Commit

```bash
git add src/api/routers/pages.py
git commit -m "feat(api): port HTMX page routes to FastAPI with Jinja2Templates"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Pages router exists
test -f src/api/routers/pages.py && echo "OK: pages router"

# 2. Router is importable
python3 -c "
from src.api.routers.pages import router
print(f'Page routes: {len(router.routes)}')
print('OK: pages router importable')
"

# 3. Templates directory is referenced
grep -q "web_interface/templates" src/api/routers/pages.py && echo "OK: templates path configured"

# 4. All partials are handled
for partial in overview general display durations schedule weather stocks plugins fonts logs raw-json wifi cache operation-history; do
  grep -q "$partial" src/api/routers/pages.py && echo "OK: $partial handled"
done
```

---

## Notes

- This is a **temporary** migration. Phase 3 replaces all Jinja2 templates with an Angular SPA. Keep the code simple and mechanical -- do not refactor the templates.
- Flask's `flash()` function uses sessions. FastAPI does not have built-in session support. Options: (a) use `starlette-session`, (b) pass errors as query parameters, (c) use HTMX's `HX-Trigger` header with a client-side toast. Option (c) is recommended as it aligns with the HTMX pattern already in use.
- Flask's `url_for()` is used in templates to generate URLs. FastAPI has `request.url_for()` but it needs to be passed to the template context. Alternatively, hardcode the known paths since they are stable.
- The `saved_repositories_manager` attribute assignment pattern from Flask (`pages_v3.saved_repositories_manager = ...`) is replaced by FastAPI dependency injection.
