# DOCK-004 — Development Compose Overlay

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** [DOCK-003](DOCK-003-compose-production.md)
**Blocks:** _(none)_

---

## Context

The ROADMAP specifies a `compose.dev.yml` overlay that mounts source code for live reload and enables emulator mode. This allows developers to run the full stack in Docker without hardware, with code changes reflected immediately without rebuilding the image.

The overlay uses `docker compose -f compose.yml -f compose.dev.yml up` to merge the dev configuration on top of the production base.

---

## Acceptance Criteria

- [ ] `compose.dev.yml` exists at the repository root
- [ ] Overlay enables `EMULATOR=true` for the display service
- [ ] Source directories (`src/`, `plugins/`, `config/`, `fonts/`) are bind-mounted for live reload
- [ ] `privileged` mode and device mounts are removed (not needed for emulator)
- [ ] Web service mounts source for live reload
- [ ] Angular dev server or hot-reload is supported
- [ ] `docker compose -f compose.yml -f compose.dev.yml config` validates successfully

---

## Implementation Checklist

### 1. Create compose.dev.yml

- [ ] Create `compose.dev.yml` at the repo root
- [ ] Override `display` service:
  - [ ] Set `environment: EMULATOR=true`
  - [ ] Remove `privileged: true` (set to `false`)
  - [ ] Remove `devices` list
  - [ ] Add bind mounts for source: `./src:/app/src`, `./run.py:/app/run.py`, `./config:/app/config`, `./plugins:/app/plugins`, `./fonts:/app/fonts`
- [ ] Override `web` service:
  - [ ] Add bind mounts for source: `./src:/app/src`, `./config:/app/config`
  - [ ] Set `environment: LEDMATRIX_DEBUG=true`
- [ ] Optionally add a `frontend` service:
  - [ ] `image: node:22-slim`
  - [ ] `command: npx ng serve --host 0.0.0.0`
  - [ ] `ports: ["4200:4200"]`
  - [ ] Bind mount `./frontend:/app/frontend`
  - [ ] This provides Angular hot-reload during development

### 2. Add convenience script or Makefile target

- [ ] Add a comment or note in the file header showing the usage pattern:
  ```
  # Usage: docker compose -f compose.yml -f compose.dev.yml up
  ```

### 3. Commit

```bash
git add compose.dev.yml
git commit -m "feat(docker): add dev Compose overlay with emulator mode and source mounts"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. File exists
test -f compose.dev.yml && echo "OK: compose.dev.yml exists"

# 2. Emulator environment set
grep -q "EMULATOR" compose.dev.yml && echo "OK: EMULATOR env var present"

# 3. Source bind mounts present
grep -q "./src:/app/src" compose.dev.yml && echo "OK: src bind mount"

# 4. Privileged mode disabled
grep -q "privileged.*false" compose.dev.yml && echo "OK: privileged disabled" || echo "INFO: check privileged override"

# 5. Combined config validates (requires Docker)
docker compose -f compose.yml -f compose.dev.yml config > /dev/null 2>&1 && echo "OK: combined config valid" || echo "SKIP: Docker not available"
```

---

## Notes

- Bind mounts override named volumes from the base `compose.yml`. The dev overlay uses the host filesystem directly, so changes are reflected immediately.
- The Angular dev server (port 4200) is optional in the overlay. Developers can also run `ng serve` on the host and proxy to the containerized API.
- Do NOT mount `.venv/` or `node_modules/` from the host -- the container has its own dependency installations.
- Live reload for the Python display service may require restarting the container (no watchdog in `run.py`). The web service uses uvicorn's built-in reload if `--reload` is added to the command.
- Consider adding `command: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 5000 --reload` to the web service override for auto-reload.
