# FRONT-007 — Logs and Store Feature Modules

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-003](FRONT-003-api-service-layer.md), [FRONT-002](FRONT-002-primeng-theme-layout.md)
**Blocks:** _(none)_

---

## Context

Two remaining feature modules from the ROADMAP: Logs (live log stream viewer) and Store (plugin marketplace). These replace the HTMX `logs.html` partial and the plugin store functionality in the existing UI.

**Logs:** The backend streams log entries via SSE at `/api/v3/stream/logs` (every ~5 seconds) and provides historical logs via `GET /api/v3/logs`. The current HTMX version renders logs as a scrolling text area with auto-scroll.

**Store:** The backend provides store operations at `/api/v3/plugins/store/` for browsing available plugins, installing, updating, and uninstalling. The current HTMX version uses `plugins_manager.js` for store interactions.

---

## Acceptance Criteria

- [ ] Logs route is lazy-loaded at `/logs`
- [ ] Logs view shows live streaming log entries via SSE
- [ ] Log entries are syntax-highlighted by level (error=red, warn=yellow, info=default, debug=gray)
- [ ] Auto-scroll to bottom with toggle to pause auto-scroll
- [ ] Log level filter (all, error, warn, info, debug)
- [ ] Store route is lazy-loaded at `/store`
- [ ] Store view lists available plugins from the registry with search
- [ ] Each store card shows: name, description, version, installed status
- [ ] Install button triggers `POST /api/v3/plugins/store/install`
- [ ] Update button visible when newer version available

---

## Implementation Checklist

### 1. Create logs module

- [ ] Create `frontend/src/app/features/logs/` directory
- [ ] Add lazy route in `app.routes.ts`: `{ path: 'logs', loadComponent: () => import(...) }`
- [ ] Create `LogViewerComponent` as the main component

### 2. Build log viewer

- [ ] Subscribe to `SseService.logStream$` for live log entries
- [ ] Display in a virtual-scroll container (PrimeNG `VirtualScroller` or custom)
- [ ] Color-code log entries by level using CSS classes
- [ ] Auto-scroll to newest entry by default
- [ ] "Pause scroll" toggle button (PrimeNG `ToggleButton`) to freeze scroll position
- [ ] Log level filter dropdown using PrimeNG `Dropdown`
- [ ] "Clear" button to reset the displayed log buffer (client-side only)

### 3. Create store module

- [ ] Create `frontend/src/app/features/store/` directory
- [ ] Add lazy route in `app.routes.ts`: `{ path: 'store', loadComponent: () => import(...) }`
- [ ] Create `StoreComponent` as the main component

### 4. Build store plugin browser

- [ ] Fetch available plugins from `GET /api/v3/plugins/store/available`
- [ ] Display in PrimeNG `DataView` with grid layout
- [ ] Search bar with PrimeNG `InputText` filtering by name and description
- [ ] Each card shows: plugin name, description, latest version, author
- [ ] "Installed" badge on plugins that are already installed
- [ ] "Update available" badge when installed version < store version

### 5. Add install/update/uninstall actions

- [ ] Install button calls `POST /api/v3/plugins/store/install` with `{ plugin_id: ... }`
- [ ] Update button calls `POST /api/v3/plugins/store/update` with `{ plugin_id: ... }`
- [ ] Uninstall button with confirmation dialog calls `POST /api/v3/plugins/store/uninstall`
- [ ] Show PrimeNG `ProgressSpinner` during install/update operations
- [ ] Toast notification on success/failure

### 6. Commit

```bash
git add frontend/src/app/features/logs/ frontend/src/app/features/store/
git commit -m "feat(frontend): add logs viewer and plugin store modules"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Log components exist
test -f frontend/src/app/features/logs/log-viewer/log-viewer.component.ts && echo "OK: log viewer"

# 2. Store components exist
test -f frontend/src/app/features/store/store.component.ts && echo "OK: store component"

# 3. Routes configured
grep -q "logs" frontend/src/app/app.routes.ts && echo "OK: logs route"
grep -q "store" frontend/src/app/app.routes.ts && echo "OK: store route"

# 4. Build succeeds
cd frontend && npx ng build && echo "OK: build with logs and store"
```

---

## Notes

- The log stream SSE sends batches of log lines every ~5 seconds. Parse the JSON payload to extract individual log entries.
- Virtual scrolling is important for logs performance. Without it, accumulating thousands of log entries will degrade browser performance. Cap the client-side buffer at ~5000 entries and discard oldest.
- The store API may return a 503 if the registry is unreachable. Show an "Unable to reach plugin store" empty state.
- Install/update operations can take 10-30 seconds (pip install + dependency resolution). The UI must remain responsive during this time.
- The `operation-history` partial from HTMX is deferred to SPIKE-003 -- it shows recent store operations.
