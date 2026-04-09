# FRONT-006 — Settings Feature Module

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-002](FRONT-002-primeng-theme-layout.md), [FRONT-003](FRONT-003-api-service-layer.md)
**Blocks:** _(none)_

---

## Context

The Settings module replaces multiple HTMX partials: `general.html`, `display.html`, `durations.html`, `schedule.html`, `weather.html`, `stocks.html`, `fonts.html`, `wifi.html`, and `cache.html`. These configure system-wide settings for the LED matrix display.

The backend provides:
- `GET/POST /api/v3/config/main` -- full config (display, schedule, brightness, plugin durations)
- `GET/POST /api/v3/config/schedule` -- on/off schedule
- `GET/POST /api/v3/config/dim-schedule` -- brightness schedule
- `GET /api/v3/config/secrets` -- API keys (redacted)
- `GET /api/v3/fonts` -- font list
- `POST /api/v3/fonts/upload` -- font upload
- `GET /api/v3/wifi/scan` -- Wi-Fi networks
- `POST /api/v3/wifi/connect` -- connect to network

---

## Acceptance Criteria

- [ ] Settings route is lazy-loaded at `/settings`
- [ ] Tabbed interface with sections: General, Display, Schedule, Fonts, Wi-Fi
- [ ] General tab: brightness, rotation, display dimensions config
- [ ] Display tab: plugin durations, transition settings
- [ ] Schedule tab: on/off times, dim schedule with time picker
- [ ] Fonts tab: list installed fonts, upload new fonts
- [ ] Wi-Fi tab: scan networks, connect to a network
- [ ] All settings saved via config API with toast notifications

---

## Implementation Checklist

### 1. Create settings module structure

- [ ] Create `frontend/src/app/features/settings/` directory
- [ ] Add lazy route in `app.routes.ts`: `{ path: 'settings', loadComponent: () => import(...) }`

### 2. Build tabbed layout

- [ ] Create `SettingsComponent` using PrimeNG `TabView` with tab panels
- [ ] Each tab is a standalone child component for separation of concerns

### 3. General settings tab

- [ ] Create `GeneralSettingsComponent`
- [ ] Brightness slider using PrimeNG `Slider`
- [ ] Rotation dropdown (0, 90, 180, 270 degrees)
- [ ] Matrix dimensions display (read-only, from system config)

### 4. Display settings tab

- [ ] Create `DisplaySettingsComponent`
- [ ] Plugin duration configuration per-plugin using PrimeNG `InputNumber`
- [ ] Transition type dropdown (redraw, fade, slide)
- [ ] Transition speed slider

### 5. Schedule settings tab

- [ ] Create `ScheduleSettingsComponent`
- [ ] On/off schedule with PrimeNG `Calendar` time pickers
- [ ] Dim schedule entries with time range and brightness level
- [ ] Add/remove dim schedule entries

### 6. Fonts tab

- [ ] Create `FontsSettingsComponent`
- [ ] List installed fonts from `GET /api/v3/fonts`
- [ ] Upload font via PrimeNG `FileUpload` to `POST /api/v3/fonts/upload`
- [ ] Show upload progress and success/error feedback

### 7. Wi-Fi tab

- [ ] Create `WifiSettingsComponent`
- [ ] Scan button triggers `GET /api/v3/wifi/scan`
- [ ] Display available networks in PrimeNG `Table`
- [ ] Connect dialog with password input using PrimeNG `Dialog` + `Password`

### 8. Commit

```bash
git add frontend/src/app/features/settings/
git commit -m "feat(frontend): add settings module with tabbed config UI"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Settings components exist
test -f frontend/src/app/features/settings/settings.component.ts && echo "OK: settings component"
test -f frontend/src/app/features/settings/general/general-settings.component.ts && echo "OK: general tab"
test -f frontend/src/app/features/settings/display/display-settings.component.ts && echo "OK: display tab"
test -f frontend/src/app/features/settings/schedule/schedule-settings.component.ts && echo "OK: schedule tab"
test -f frontend/src/app/features/settings/fonts/fonts-settings.component.ts && echo "OK: fonts tab"
test -f frontend/src/app/features/settings/wifi/wifi-settings.component.ts && echo "OK: wifi tab"

# 2. Route configured
grep -q "settings" frontend/src/app/app.routes.ts && echo "OK: settings route"

# 3. Build succeeds
cd frontend && npx ng build && echo "OK: build with settings module"
```

---

## Notes

- The existing HTMX partials make heavy use of `hx-post` for inline saves. The Angular version uses explicit Save buttons with form validation.
- Wi-Fi scan may not work in emulator/development environments. Handle the 503 response gracefully with a "Wi-Fi not available" message.
- Font upload uses multipart form data. PrimeNG `FileUpload` handles this natively.
- The raw JSON editor (`raw_json.html` in HTMX) is deferred to SPIKE-002 -- it is a power-user feature.
- Schedule times should use 24-hour format for consistency with the backend config.
