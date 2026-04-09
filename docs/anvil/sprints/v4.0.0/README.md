# Sprint v4.0.0 -- Containerization

**Goal:** Establish a Docker-first deployment model so LEDMatrix runs as a privileged container on Raspberry Pi, with a dev-friendly emulator mode via Docker Compose overlays.

**ROADMAP phase:** Phase 4

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [DOCK-001](DOCK-001-dockerfile-multi-stage.md) | Multi-stage Dockerfile | Open | -- |
| [DOCK-002](DOCK-002-dockerignore.md) | .dockerignore file | Open | -- |
| [DOCK-003](DOCK-003-compose-production.md) | Production Docker Compose | Open | DOCK-001 |
| [DOCK-004](DOCK-004-compose-dev-overlay.md) | Development Compose overlay | Open | DOCK-003 |
| [DOCK-005](DOCK-005-cli-docker-commands.md) | Matrix CLI docker command group | Open | DOCK-003 |
| [DOCK-006](DOCK-006-systemd-docker-units.md) | Systemd units for Docker deployment | Open | DOCK-003 |
| [DOCK-007](DOCK-007-install-docker-detection.md) | matrix install Docker detection | Open | DOCK-005, DOCK-006 |
| [SPIKE-001](SPIKE-001-rgbmatrix-in-container.md) | SPIKE: rgbmatrix library in container | Open | DOCK-001 |
| [SPIKE-002](SPIKE-002-pi-gpio-device-permissions.md) | SPIKE: Pi GPIO/device permissions | Open | DOCK-003 |
| [SPIKE-003](SPIKE-003-ci-docker-build.md) | SPIKE: CI pipeline for Docker image build | Open | DOCK-001 |

## Dependency Graph

```
DOCK-001 (Dockerfile)
  +-- DOCK-003 (compose.yml)
  |     +-- DOCK-004 (compose.dev.yml)
  |     +-- DOCK-005 (CLI docker commands)
  |     |     +-- DOCK-007 (install Docker detection)
  |     +-- DOCK-006 (systemd Docker units)
  |           +-- DOCK-007 (install Docker detection)
DOCK-002 (.dockerignore)
SPIKE-001 (rgbmatrix in container)
SPIKE-002 (Pi GPIO permissions)
SPIKE-003 (CI Docker build)
```

## Definition of Done (Phase 4)

- [ ] Multi-stage Dockerfile builds Angular SPA and Python runtime in a single image
- [ ] `docker build .` produces a working image with `uv`-installed dependencies
- [ ] `compose.yml` runs display + web services with named volumes for config, data, fonts
- [ ] `compose.dev.yml` overlay enables emulator mode with source mounts for live reload
- [ ] `matrix docker start|stop|logs|update|build` CLI commands work
- [ ] Pi deployment uses `--privileged` with `/dev/mem` and `/dev/gpiomem` mounts
- [ ] Systemd unit files manage Docker containers instead of bare processes
- [ ] `matrix install` detects Docker availability and offers container vs. native install
- [ ] Emulator mode works without hardware mounts (`EMULATOR=true`)
- [ ] No regressions in backend Python tests
- [ ] No regressions in Angular build or tests
- [ ] Plugin impact: none (Phase 4 is deployment-only; no plugin API changes)

## Architecture Notes

### New files created in Phase 4

```
Dockerfile                          # Multi-stage build (Angular + Python)
.dockerignore                       # Exclude .git, .venv, node_modules, etc.
compose.yml                         # Production stack: display + web services
compose.dev.yml                     # Dev overlay: emulator, source mounts, live reload
systemd/ledmatrix-docker.service    # Systemd unit for Docker Compose stack
```

### Modified files

```
scripts/matrix_cli.py               # New `docker` command group (~5 subcommands)
systemd/ledmatrix.service           # Preserved for native install (not replaced)
systemd/ledmatrix-web.service       # Preserved for native install (not replaced)
```

### Container architecture

```
+---------------------------+
| Docker Container          |
|                           |
|  Stage 1: node:22-slim    |
|    npm install + ng build |
|    -> /app/frontend/dist/ |
|                           |
|  Stage 2: python:3.12-slim|
|    uv sync (deps)         |
|    COPY --from=stage1 dist|
|    COPY src/ plugins/ ... |
|                           |
|  Entrypoint:              |
|    run.py (display)       |
|    OR src/api/start.py    |
+---------------------------+
       |
       | --privileged (Pi only)
       | /dev/mem, /dev/gpiomem
       |
+------+------+
| Host volumes |
|  config/     |
|  fonts/      |
|  data/       |
+--------------+
```

### Key technical decisions

- **Single image, two services:** The same Docker image runs as either the display service or the web/API service, controlled by the entrypoint/command override in Compose.
- **`uv` inside the container:** Dependencies installed via `uv sync` in the Dockerfile, matching the host dev workflow.
- **Named volumes:** `config/`, `fonts/`, and plugin data persist across container restarts and image updates.
- **Privileged mode for Pi only:** The production `compose.yml` includes device mounts; the dev overlay disables them and sets `EMULATOR=true`.
- **Native install preserved:** Existing systemd units and bare-metal install path remain functional. Docker is an alternative, not a replacement.
