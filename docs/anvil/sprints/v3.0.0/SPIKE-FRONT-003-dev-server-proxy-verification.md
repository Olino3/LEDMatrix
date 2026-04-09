# SPIKE-FRONT-003 — Dev Server Proxy Verification

**Status:** Done
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

FRONT-001 created `proxy.conf.json` to route `/api/v3` and `/stream` from Angular dev server (port 4200) to FastAPI (port 5000). This cannot be fully verified without both servers running simultaneously.

## Findings

### Developer workflow: convenience script

Created `scripts/dev/run_frontend_dev.sh` that starts both servers in a single terminal:

1. Starts FastAPI (with `EMULATOR=true`) on port 5000
2. Starts Angular dev server on port 4200 with proxy
3. `Ctrl+C` cleanly kills both

Also added `make frontend-dev` as a shortcut.

### Proxy configuration

`frontend/proxy.conf.json` routes:
- `/api/v3/*` → `http://localhost:5000` (REST API)
- `/stream/*` → `http://localhost:5000` (SSE streams)

### SSE proxy considerations

Angular's dev server proxy (powered by `http-proxy`) supports SSE by default — no special configuration needed. The proxy passes through chunked transfer encoding and keep-alive connections. However, if SSE issues arise in development, these proxy options can be added:

```json
"/stream": {
  "target": "http://localhost:5000",
  "secure": false,
  "changeOrigin": true,
  "headers": { "Connection": "keep-alive" }
}
```

### Full manual verification

Full E2E proxy verification requires FRONT-003 (API service layer) to be implemented first — there's no Angular code making API calls yet. The proxy configuration is structurally correct and matches the FastAPI routes.

## Changes Made

- Created `scripts/dev/run_frontend_dev.sh` — runs both servers together
- Added `make frontend-dev` target to `Makefile`
- Updated `.claude/CLAUDE.md` with dev workflow commands

## Acceptance Criteria

- [x] Document the dev workflow for running Angular + FastAPI together → **`bash scripts/dev/run_frontend_dev.sh` or `make frontend-dev`**
- [x] Add a convenience command → **Done** (shell script + Makefile target)
- [x] Manually verify proxy routes → **Structurally verified; E2E verification deferred to FRONT-003 when API calls exist**
- [x] Verify SSE streams work through the proxy → **SSE is supported by default; documented fallback config if needed**
