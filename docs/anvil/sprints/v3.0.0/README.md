# Sprint v3.0.0 -- Frontend Modernization

**Goal:** Replace the Jinja2/HTMX frontend with an Angular 17+ SPA using PrimeNG, featuring lazy-loaded feature modules, real-time SSE streams, and a dark-first responsive design.

**ROADMAP phase:** Phase 3

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [FRONT-001](FRONT-001-angular-project-scaffold.md) | Angular project scaffold | **Done** | -- |
| [FRONT-002](FRONT-002-primeng-theme-layout.md) | PrimeNG integration and dark theme layout | **Done** | FRONT-001 |
| [FRONT-003](FRONT-003-api-service-layer.md) | API service layer and SSE client | **Done** | FRONT-001 |
| [FRONT-003a](FRONT-003a-font-service.md) | Font service | Open | FRONT-003 |
| [FRONT-003b](FRONT-003b-wifi-service.md) | WiFi service | Open | FRONT-003 |
| [FRONT-003c](FRONT-003c-starlark-service.md) | Starlark service | Open | FRONT-003 |
| [FRONT-004](FRONT-004-dashboard-module.md) | Dashboard feature module | Open | FRONT-002, FRONT-003 |
| [FRONT-005](FRONT-005-plugins-module.md) | Plugins feature module | Open | FRONT-002, FRONT-003, FRONT-003c |
| [FRONT-006](FRONT-006-settings-module.md) | Settings feature module | Open | FRONT-002, FRONT-003, FRONT-003a, FRONT-003b |
| [FRONT-007](FRONT-007-logs-store-modules.md) | Logs and Store feature modules | Open | FRONT-002, FRONT-003 |
| [FRONT-008](FRONT-008-htmx-removal-cleanup.md) | HTMX removal and legacy frontend cleanup | Open | FRONT-004, FRONT-005, FRONT-006, FRONT-007 |
| [SPIKE-001](SPIKE-001-angular-unit-test-setup.md) | Angular unit test setup | Open | FRONT-001 |
| [SPIKE-002](SPIKE-002-raw-json-editor.md) | Raw JSON config editor | Open | FRONT-006 |
| [SPIKE-003](SPIKE-003-operation-history-view.md) | Operation history view | Open | FRONT-007 |
| [SPIKE-004](SPIKE-004-ci-angular-build.md) | CI pipeline for Angular build and tests | Open | FRONT-001, SPIKE-001 |
| [SPIKE-005](SPIKE-005-starlark-config-ui.md) | Starlark configuration UI | Open | FRONT-006 |
| [SPIKE-FRONT-001](SPIKE-FRONT-001-nodejs-in-distrobox.md) | Node.js in distrobox | **Done** | FRONT-001 |
| [SPIKE-FRONT-002](SPIKE-FRONT-002-angular-environment-switching.md) | Angular environment file switching | **Done** | FRONT-001 |
| [SPIKE-FRONT-003](SPIKE-FRONT-003-dev-server-proxy-verification.md) | Dev server proxy verification | **Done** | FRONT-001 |

## Dependency Graph

```
FRONT-001 (Angular scaffold)
  +-- FRONT-002 (PrimeNG + dark theme layout)
  |     +-- FRONT-004 (Dashboard module)
  |     +-- FRONT-005 (Plugins module)
  |     +-- FRONT-006 (Settings module)
  |     |     +-- SPIKE-002 (Raw JSON editor)
  |     |     +-- SPIKE-005 (Starlark config UI)
  |     +-- FRONT-007 (Logs + Store modules)
  |           +-- SPIKE-003 (Operation history)
  +-- FRONT-003 (API service layer + SSE)
  |     +-- FRONT-003a (Font service)
  |     |     +-- FRONT-006 (Settings module)
  |     +-- FRONT-003b (WiFi service)
  |     |     +-- FRONT-006 (Settings module)
  |     +-- FRONT-003c (Starlark service)
  |     |     +-- FRONT-005 (Plugins module)
  |     +-- FRONT-004 (Dashboard module)
  |     +-- FRONT-005 (Plugins module)
  |     +-- FRONT-006 (Settings module)
  |     +-- FRONT-007 (Logs + Store modules)
  +-- SPIKE-001 (Angular test setup)
  |     +-- SPIKE-004 (CI Angular build)
  +-- SPIKE-004 (CI Angular build)

FRONT-004 + FRONT-005 + FRONT-006 + FRONT-007
  +-- FRONT-008 (HTMX removal + cleanup)
```

## Definition of Done (Phase 3)

- [x] Angular 21 SPA in `frontend/` with PrimeNG component library
- [ ] Dark-first theme active by default, responsive layout (mobile/tablet/desktop)
- [ ] Five lazy-loaded feature modules: Dashboard, Plugins, Settings, Logs, Store
- [ ] Dashboard shows real-time system metrics and display preview via SSE
- [ ] Plugin config forms dynamically generated from JSON Schema
- [ ] All HTMX templates and legacy static files removed
- [ ] `src/api/routers/pages.py` (HTMX page routes) removed
- [x] FastAPI serves the built Angular SPA from `/`
- [x] `ng build` produces a valid production bundle
- [ ] Angular unit tests pass in CI (headless Chrome)
- [ ] No regressions in backend Python tests
- [ ] Plugin impact: none (Phase 3 is frontend-only; no plugin API changes)

## Architecture Notes

### New directory structure after Phase 3

```
frontend/
  angular.json
  package.json
  proxy.conf.json
  src/
    app/
      app.component.ts
      app.config.ts
      app.routes.ts
      core/
        models/           # TypeScript interfaces matching Pydantic models
        services/         # ApiService, SseService, SystemService, etc.
        interceptors/     # Error interceptor
      layout/
        app-layout.component.ts
        sidebar/
        topbar/
      features/
        dashboard/        # System stats, active plugin, display preview
        plugins/          # Plugin list, config editor, schema-driven forms
        settings/         # Tabbed config: general, display, schedule, fonts, wifi
        logs/             # Live log stream viewer
        store/            # Plugin marketplace browser
      shared/
        loading/
        error-state/
        empty-state/
        schema-form/      # Dynamic JSON Schema form generator
    environments/
  dist/
    ledmatrix/
      browser/            # Production build output, served by FastAPI
```

### Files removed in Phase 3

- `web_interface/templates/` -- all Jinja2/HTMX templates (16 files)
- `web_interface/static/` -- all CSS, JS, images (htmx, alpine, tailwind, app.js)
- `src/api/routers/pages.py` -- HTMX page router

### Files preserved

- `web_interface/cache.py` -- if still used by backend services
- `web_interface_v2.py` / `src/web_interface/` -- compatibility shim (until Phase 9)

### Key technical decisions

- **Angular 17+ standalone components** -- no NgModules, simplifies lazy loading
- **PrimeNG v17+** -- standalone component imports, Aura Dark theme preset
- **SSE via native EventSource** -- no WebSocket (backend only supports SSE currently)
- **Dynamic JSON Schema forms** -- plugin config forms generated from `config_schema.json`
- **SPA serving** -- FastAPI mounts `frontend/dist/` with catch-all for client-side routing
