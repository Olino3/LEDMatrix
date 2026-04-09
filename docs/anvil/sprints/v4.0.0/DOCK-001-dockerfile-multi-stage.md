# DOCK-001 — Multi-stage Dockerfile

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** _(none -- start here)_
**Blocks:** [DOCK-003](DOCK-003-compose-production.md), [SPIKE-001](SPIKE-001-rgbmatrix-in-container.md), [SPIKE-003](SPIKE-003-ci-docker-build.md)

---

## Context

Phase 4 introduces a Docker-first deployment model. This ticket creates the multi-stage Dockerfile that builds both the Angular SPA and the Python runtime into a single image.

The build has two stages:
1. **Stage 1 (Node):** Installs npm dependencies and runs `ng build` to produce the Angular SPA in `frontend/dist/ledmatrix/browser/`.
2. **Stage 2 (Python):** Uses `python:3.12-slim` as the base, installs `uv` for dependency management, copies the built SPA from stage 1, and installs all Python dependencies.

The image must support two runtime modes:
- **Hardware mode (Pi):** Requires `rgbmatrix` C library and `/dev` device access at runtime.
- **Emulator mode (dev):** Uses `RGBMatrixEmulator` via the `EMULATOR=true` environment variable, no hardware needed.

---

## Acceptance Criteria

- [ ] `Dockerfile` exists at the repository root
- [ ] Stage 1 uses a Node base image and produces the Angular production build
- [ ] Stage 2 uses `python:3.12-slim` and installs dependencies via `uv`
- [ ] The built Angular SPA is copied from stage 1 into the final image
- [ ] Source code (`src/`, `run.py`, `scripts/`, `plugins/`) is copied into the image
- [ ] Default entrypoint runs the display controller (`run.py`)
- [ ] `EMULATOR` environment variable is respected at runtime
- [ ] Image builds successfully with `docker build -t ledmatrix .`

---

## Implementation Checklist

### 1. Create the Dockerfile

- [ ] Create `Dockerfile` at the repo root
- [ ] Stage 1: `FROM node:22-slim AS frontend-build`
  - [ ] Set `WORKDIR /app/frontend`
  - [ ] Copy `frontend/package.json` and `frontend/package-lock.json`
  - [ ] Run `npm ci` for reproducible installs
  - [ ] Copy the rest of `frontend/`
  - [ ] Run `npx ng build` to produce production output
- [ ] Stage 2: `FROM python:3.12-slim AS runtime`
  - [ ] Install system dependencies: `libfreetype6`, `libjpeg62-turbo`, `libsdl2-2.0-0` (runtime-only, not dev headers)
  - [ ] Install `uv` via `pip install uv` or the official installer script
  - [ ] Set `WORKDIR /app`
  - [ ] Copy `pyproject.toml` and `uv.lock`
  - [ ] Run `uv sync --no-dev --extra emulator` to install Python dependencies
  - [ ] Copy source code: `src/`, `run.py`, `scripts/`, `config/config.template.json`
  - [ ] Copy `COPY --from=frontend-build /app/frontend/dist /app/frontend/dist`
  - [ ] Copy `fonts/`, `plugin-repos/` directories
  - [ ] Set `ENV PYTHONDONTWRITEBYTECODE=1`
  - [ ] Set default `CMD ["python", "run.py"]`

### 2. Verify the build

- [ ] Run `docker build -t ledmatrix:dev .` and confirm it completes
- [ ] Run `docker run --rm -e EMULATOR=true ledmatrix:dev` and confirm it starts (will fail without display, but should not crash on import)

### 3. Commit

```bash
git add Dockerfile
git commit -m "feat(docker): add multi-stage Dockerfile for Angular + Python build"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Dockerfile exists
test -f Dockerfile && echo "OK: Dockerfile exists"

# 2. Dockerfile has two FROM stages
grep -c "^FROM" Dockerfile | grep -q "2" && echo "OK: multi-stage build"

# 3. Stage 1 uses Node
grep -q "node:" Dockerfile && echo "OK: Node stage present"

# 4. Stage 2 uses python:3.12-slim
grep -q "python:3.12-slim" Dockerfile && echo "OK: Python base image"

# 5. uv is installed in the image
grep -q "uv" Dockerfile && echo "OK: uv referenced in Dockerfile"

# 6. Angular build output is copied
grep -q "frontend-build" Dockerfile && echo "OK: frontend build stage referenced"

# 7. Image builds (requires Docker)
docker build -t ledmatrix:test . && echo "OK: image builds" || echo "SKIP: Docker not available"
```

---

## Notes

- The `rgbmatrix` C library installation is complex and Pi-specific. This ticket uses the emulator extras for the base image. Hardware support is investigated in SPIKE-001.
- Do NOT copy `config/config.json` or `config/config_secrets.json` into the image -- these are user data and must be mounted as volumes.
- Do NOT copy `.venv/`, `node_modules/`, or `.git/` -- these are excluded by `.dockerignore` (DOCK-002).
- The `uv sync` command should use `--frozen` to respect the lockfile exactly.
- Consider layer caching: copy dependency files (`pyproject.toml`, `uv.lock`, `package.json`) before source code to maximize cache hits.
