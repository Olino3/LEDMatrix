# FRONT-004 — Dashboard Feature Module

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-002](FRONT-002-primeng-theme-layout.md), [FRONT-003](FRONT-003-api-service-layer.md)
**Blocks:** _(none)_

---

## Context

The Dashboard is the landing page of the Angular SPA. It replaces the HTMX "Overview" partial (`web_interface/templates/v3/partials/overview.html`) which shows system stats cards (CPU, memory, temperature, disk), active plugin info, and a live display preview.

The new Dashboard must:
- Show real-time system metrics via the SSE `/api/v3/stream/stats` stream
- Show the active plugin and display state
- Show a live display preview via the SSE `/api/v3/stream/display` stream
- Use PrimeNG components for cards, charts, and layout

The existing HTMX overview uses vanilla JavaScript with `EventSource` to update DOM elements by ID. The Angular version replaces this with reactive `Observable` subscriptions through `SseService`.

---

## Acceptance Criteria

- [ ] Dashboard route is lazy-loaded at `/` (default route)
- [ ] System stats cards display CPU, memory, temperature, disk usage with real-time updates
- [ ] Stats update via SSE stream (not polling)
- [ ] Active plugin card shows current plugin name, version, and display mode
- [ ] Live display preview shows the LED matrix image, updating at ~2 Hz via SSE
- [ ] Quick action buttons: restart display service, toggle brightness
- [ ] Dashboard handles SSE disconnection gracefully (shows stale data indicator)

---

## Implementation Checklist

### 1. Create dashboard module structure

- [ ] Create `frontend/src/app/features/dashboard/` directory
- [ ] Create `DashboardComponent` as the route entry point
- [ ] Add lazy route in `app.routes.ts`: `{ path: '', loadComponent: () => import(...) }`

### 2. Build system stats cards

- [ ] Create `StatsCardsComponent` with 4 PrimeNG `Card` components
- [ ] Subscribe to `SseService.statsStream$` for real-time CPU, memory, temp, disk
- [ ] Display values with color-coded thresholds (green < 60%, yellow < 80%, red >= 80%)
- [ ] Show "Connecting..." placeholder while SSE stream initializes

### 3. Build active plugin card

- [ ] Create `ActivePluginComponent` showing current plugin info
- [ ] Fetch active plugin from `GET /api/v3/plugins` (filter by active/displayed state)
- [ ] Show plugin name, version, display duration remaining
- [ ] Link to plugin config page

### 4. Build live display preview

- [ ] Create `DisplayPreviewComponent` subscribing to `SseService.displayStream$`
- [ ] Render base64 PNG images in an `<img>` tag, updating on each SSE event
- [ ] Scale image to fit the card while preserving aspect ratio
- [ ] Show placeholder when no preview data available

### 5. Add quick actions

- [ ] Create `QuickActionsComponent` with PrimeNG `Button` components
- [ ] "Restart Display" button calls `POST /api/v3/system/action` with `{ action: "restart" }`
- [ ] Show confirmation dialog before destructive actions using PrimeNG `ConfirmDialog`

### 6. Handle SSE lifecycle

- [ ] Unsubscribe from SSE streams on component destroy
- [ ] Show "Connection lost" indicator when SSE disconnects
- [ ] Resume display on reconnect without user action

### 7. Commit

```bash
git add frontend/src/app/features/dashboard/
git commit -m "feat(frontend): add dashboard module with live stats and display preview"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Dashboard component exists
test -f frontend/src/app/features/dashboard/dashboard.component.ts && echo "OK: dashboard component"

# 2. Sub-components exist
test -f frontend/src/app/features/dashboard/stats-cards/stats-cards.component.ts && echo "OK: stats cards"
test -f frontend/src/app/features/dashboard/display-preview/display-preview.component.ts && echo "OK: display preview"

# 3. Lazy route configured
grep -q "dashboard" frontend/src/app/app.routes.ts && echo "OK: dashboard route"

# 4. Build succeeds
cd frontend && npx ng build && echo "OK: build with dashboard"
```

---

## Notes

- The SSE stats stream sends JSON with fields: `cpu_percent`, `memory_used_percent`, `cpu_temp`, `disk_used_percent` every ~10 seconds.
- The SSE display stream sends `{ "image": "<base64-png>" }` at ~2 Hz. On resource-constrained Pi hardware, the Angular app should throttle rendering if frames arrive faster than the browser can paint.
- The current HTMX overview also shows display service status (running/stopped) from `systemctl`. This is available via `GET /api/v3/system/status` field `service_active`.
- PrimeNG `Card`, `Button`, `ConfirmDialog`, and `Tag` components are the primary building blocks here.
- Do NOT implement the full plugin list or config editing in this ticket -- that is FRONT-005.
