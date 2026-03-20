# FRONT-001 — Angular Project Scaffold

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** _(none -- start here)_
**Blocks:** [FRONT-002](FRONT-002-primeng-theme-layout.md), [FRONT-003](FRONT-003-api-service-layer.md), [FRONT-004](FRONT-004-dashboard-module.md)

---

## Context

Phase 3 replaces the Jinja2/HTMX frontend (`web_interface/templates/`, `web_interface/static/`) with an Angular 17+ single-page application. This ticket creates the Angular project skeleton in `frontend/` using Angular CLI, configures the build pipeline to output to `frontend/dist/`, and wires FastAPI to serve the built SPA.

The FastAPI backend is complete (`src/api/`) with typed Pydantic models, OpenAPI docs at `/docs`, and CORS already configured for `http://localhost:4200`. The API surface is stable at `/api/v3/`.

**Key constraints:**
- The HTMX pages router (`src/api/routers/pages.py`) and `web_interface/` static files must continue to work during the transition. They are removed in FRONT-008.
- The Angular app must be buildable independently (`ng build`) and also servable by FastAPI in production.
- Use Angular 17+ with standalone components (not NgModules) for new code.

---

## Acceptance Criteria

- [x] `frontend/` directory contains a valid Angular 21 project created via `ng new`
- [x] `angular.json` configures output to `frontend/dist/ledmatrix/`
- [x] `ng build` produces a production bundle in `frontend/dist/ledmatrix/`
- [x] `ng serve` starts dev server on port 4200 with proxy to FastAPI at port 5000
- [x] `proxy.conf.json` routes `/api/v3/*` and `/stream/*` to `http://localhost:5000`
- [x] `package.json` includes scripts: `start`, `build`, `test`, `lint`
- [x] `.gitignore` in `frontend/` ignores `node_modules/`, `dist/`, `.angular/`

---

## Implementation Checklist

### 1. Generate Angular project

- [x] Run `ng new ledmatrix --directory frontend --routing --style scss --ssr false --skip-git` (Angular 21)
- [x] Verify Angular version is 21 in `package.json`
- [x] Remove default Angular boilerplate content from `app.html` (Angular 21 naming)

### 2. Configure build output

- [x] `outputPath` defaults to `dist/ledmatrix` (no change needed)
- [x] Verify `ng build` produces `frontend/dist/ledmatrix/browser/index.html`

### 3. Configure dev proxy

- [x] Create `frontend/proxy.conf.json` routing `/api/v3` and `/stream` to `http://localhost:5000`
- [x] Update `angular.json` serve target to use `proxyConfig: "proxy.conf.json"`
- [x] Verify `ng serve` proxies API calls to FastAPI

### 4. Add environment files

- [x] Create `frontend/src/environments/environment.ts` with `apiBase: '/api/v3'`
- [x] Create `frontend/src/environments/environment.prod.ts` with same `apiBase`

### 5. Wire FastAPI to serve SPA in production

- [x] Update `src/api/main.py` with catch-all route serving SPA static files and `index.html` fallback
- [x] Catch-all does NOT intercept `/api/v3/`, `/docs`, `/redoc`, `/static/`, `/v3/`
- [x] Keep existing `/static/` mount and `/v3` page routes working alongside the SPA mount

### 6. Commit

Done across multiple commits on `feature/angular-scaffold` branch.

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Angular project structure exists
test -f frontend/package.json && echo "OK: package.json"
test -f frontend/angular.json && echo "OK: angular.json"
test -f frontend/src/app/app.component.ts && echo "OK: app.component.ts"
test -f frontend/proxy.conf.json && echo "OK: proxy.conf.json"
test -f frontend/src/environments/environment.ts && echo "OK: environment.ts"

# 2. Angular CLI builds successfully
cd frontend && npm install && npx ng build && echo "OK: ng build succeeded"

# 3. Production bundle exists
test -f frontend/dist/ledmatrix/browser/index.html && echo "OK: index.html in dist"

# 4. Proxy config is valid JSON
python3 -c "import json; json.load(open('frontend/proxy.conf.json')); print('OK: proxy config valid')"

# 5. FastAPI SPA mount code exists
grep -q "frontend/dist" src/api/main.py && echo "OK: SPA mount configured"
```

---

## Notes

- Node.js and npm are required for Angular development. The distrobox may need Node 18+ installed. This does NOT affect the Python venv.
- The Angular project uses standalone components (Angular 17+ default), not NgModules. This simplifies lazy loading in subsequent tickets.
- Do NOT add PrimeNG in this ticket -- that is FRONT-002.
- The SPA catch-all route must NOT intercept `/api/v3/`, `/docs`, `/redoc`, `/static/`, or `/v3/` paths.
- The `web_interface/` directory is preserved until FRONT-008.
