# DOCK-003 — Production Docker Compose

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** [DOCK-001](DOCK-001-dockerfile-multi-stage.md)
**Blocks:** [DOCK-004](DOCK-004-compose-dev-overlay.md), [DOCK-005](DOCK-005-cli-docker-commands.md), [DOCK-006](DOCK-006-systemd-docker-units.md)

---

## Context

The ROADMAP specifies a `compose.yml` for the full stack: a display service and a web/API service, with named volumes for persistent data. Both services use the same Docker image (built in DOCK-001) but different entrypoints.

On Raspberry Pi, the display service needs `--privileged` access and `/dev/mem`, `/dev/gpiomem` device mounts to control the LED matrix hardware. The web/API service does not need hardware access.

Pydantic Settings in the FastAPI backend already reads configuration from environment variables, so Docker environment variables can override config values without modifying files.

---

## Acceptance Criteria

- [ ] `compose.yml` exists at the repository root
- [ ] Two services defined: `display` and `web`
- [ ] Both services build from the local `Dockerfile` (or reference an image name)
- [ ] `display` service runs `run.py` as its command
- [ ] `web` service runs `src/api/start.py` as its command
- [ ] `display` service has `privileged: true` and device mounts for Pi hardware
- [ ] Named volumes defined for `config`, `fonts`, and `data`
- [ ] Both services mount the config volume at `/app/config`
- [ ] Environment variables are configurable via `.env` file or inline
- [ ] `docker compose up` starts both services

---

## Implementation Checklist

### 1. Create compose.yml

- [ ] Create `compose.yml` at the repo root (Compose v2 format, no `version:` key)
- [ ] Define `display` service:
  - [ ] `build: .` (or `image: ledmatrix:latest` for pre-built)
  - [ ] `command: python run.py`
  - [ ] `privileged: true`
  - [ ] `devices: ["/dev/mem", "/dev/gpiomem"]`
  - [ ] `restart: unless-stopped`
  - [ ] Mount named volumes: `ledmatrix-config:/app/config`, `ledmatrix-fonts:/app/fonts`, `ledmatrix-data:/app/data`
  - [ ] Environment: `PYTHONDONTWRITEBYTECODE=1`
- [ ] Define `web` service:
  - [ ] Same image as display
  - [ ] `command: python src/api/start.py`
  - [ ] `ports: ["5000:5000"]`
  - [ ] `restart: unless-stopped`
  - [ ] Mount same named volumes as display service
  - [ ] `depends_on: [display]`
- [ ] Define named volumes: `ledmatrix-config`, `ledmatrix-fonts`, `ledmatrix-data`

### 2. Create example .env file

- [ ] Create `.env.example` with documented environment variables:
  - [ ] `EMULATOR=false`
  - [ ] `LEDMATRIX_DEBUG=false`
  - [ ] `LEDMATRIX_JSON_LOGGING=true`
  - [ ] `LEDMATRIX_HOT_RELOAD=true`
- [ ] Add `.env` to `.gitignore` if not already there

### 3. Verify Compose file syntax

- [ ] Run `docker compose config` to validate the file
- [ ] Confirm both services are listed

### 4. Commit

```bash
git add compose.yml .env.example
git commit -m "feat(docker): add production Docker Compose with display and web services"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Compose file exists
test -f compose.yml && echo "OK: compose.yml exists"

# 2. Valid YAML with expected services
python3 -c "
import yaml
with open('compose.yml') as f:
    c = yaml.safe_load(f)
services = c.get('services', {})
assert 'display' in services, 'missing display service'
assert 'web' in services, 'missing web service'
print('OK: both services defined')
" 2>/dev/null || python3 -c "
import json, subprocess
result = subprocess.run(['docker', 'compose', 'config', '--format', 'json'], capture_output=True, text=True)
if result.returncode == 0:
    print('OK: compose config valid')
else:
    print('SKIP: docker compose not available')
"

# 3. Named volumes defined
grep -q "ledmatrix-config" compose.yml && echo "OK: config volume"
grep -q "ledmatrix-fonts" compose.yml && echo "OK: fonts volume"

# 4. Privileged mode for display
grep -q "privileged" compose.yml && echo "OK: privileged mode set"

# 5. Web service exposes port 5000
grep -q "5000" compose.yml && echo "OK: port 5000 exposed"

# 6. .env.example exists
test -f .env.example && echo "OK: .env.example exists"
```

---

## Notes

- The `privileged: true` flag and device mounts are only needed on Raspberry Pi. For non-Pi hosts, these settings are harmless but unnecessary -- the dev overlay (DOCK-004) removes them.
- Do NOT hardcode API keys or secrets in `compose.yml`. Secrets should be passed via `.env` file or Docker secrets.
- The `display` and `web` services share volumes so they can both read the same config and font files.
- Plugin data (downloaded plugin assets, caches) should persist in the `ledmatrix-data` volume.
- The Compose file uses `build: .` for local builds. For published images, this would change to `image: ghcr.io/olino3/ledmatrix:latest` or similar.
