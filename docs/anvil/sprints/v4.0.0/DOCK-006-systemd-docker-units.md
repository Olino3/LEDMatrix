# DOCK-006 — Systemd Units for Docker Deployment

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** [DOCK-003](DOCK-003-compose-production.md)
**Blocks:** [DOCK-007](DOCK-007-install-docker-detection.md)

---

## Context

Currently, LEDMatrix uses two systemd unit files (`systemd/ledmatrix.service` and `systemd/ledmatrix-web.service`) that run Python processes directly. For Docker deployments, a single systemd unit should manage the Docker Compose stack instead.

The existing native units are preserved for users who prefer bare-metal installs. The new Docker unit is an alternative, not a replacement. The `matrix install` command (DOCK-007) will choose which units to install based on whether Docker is available.

---

## Acceptance Criteria

- [ ] `systemd/ledmatrix-docker.service` template file exists
- [ ] Unit starts the Docker Compose stack with `docker compose up`
- [ ] Unit stops containers with `docker compose down` on service stop
- [ ] Unit depends on `docker.service` being active
- [ ] Template uses `__PROJECT_ROOT_DIR__` placeholder (matching existing convention)
- [ ] Existing native units (`ledmatrix.service`, `ledmatrix-web.service`) are not modified
- [ ] Unit supports `systemctl status ledmatrix-docker` for health checking

---

## Implementation Checklist

### 1. Create Docker systemd unit template

- [ ] Create `systemd/ledmatrix-docker.service`
- [ ] Set `After=docker.service network-online.target`
- [ ] Set `Requires=docker.service`
- [ ] Set `WorkingDirectory=__PROJECT_ROOT_DIR__`
- [ ] Set `ExecStart=/usr/bin/docker compose -f __PROJECT_ROOT_DIR__/compose.yml up`
- [ ] Set `ExecStop=/usr/bin/docker compose -f __PROJECT_ROOT_DIR__/compose.yml down`
- [ ] Set `Restart=on-failure` with `RestartSec=15`
- [ ] Set `Type=simple` (docker compose up runs in foreground without `-d`)
- [ ] Set `SyslogIdentifier=ledmatrix-docker`
- [ ] Add `[Install]` section with `WantedBy=multi-user.target`

### 2. Document the unit

- [ ] Add a comment header explaining this is for Docker deployments
- [ ] Note that `__PROJECT_ROOT_DIR__` is replaced during `matrix install`

### 3. Commit

```bash
git add systemd/ledmatrix-docker.service
git commit -m "feat(docker): add systemd unit template for Docker Compose stack"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. File exists
test -f systemd/ledmatrix-docker.service && echo "OK: docker unit exists"

# 2. Depends on docker.service
grep -q "docker.service" systemd/ledmatrix-docker.service && echo "OK: docker dependency"

# 3. Uses compose commands
grep -q "docker compose" systemd/ledmatrix-docker.service && echo "OK: compose in ExecStart"

# 4. Has placeholder for project root
grep -q "__PROJECT_ROOT_DIR__" systemd/ledmatrix-docker.service && echo "OK: path placeholder"

# 5. Existing units unchanged
git diff --name-only systemd/ledmatrix.service systemd/ledmatrix-web.service 2>/dev/null | wc -l | grep -q "0" && echo "OK: native units unchanged"
```

---

## Notes

- The unit runs `docker compose up` (without `-d`) so systemd can track the process lifecycle. Detached mode would cause systemd to think the service exited immediately.
- `Type=simple` is correct because `docker compose up` (foreground) is the main process.
- The `ExecStop` command ensures containers are stopped cleanly when the systemd service is stopped.
- On Pi, the Docker daemon itself is a separate service (`docker.service`). The `Requires=` directive ensures it starts first.
- Do NOT add the unit to systemd in this ticket. The `matrix install` flow (DOCK-007) handles installation and path substitution.
