# DOCK-007 — matrix install Docker Detection

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** [DOCK-005](DOCK-005-cli-docker-commands.md), [DOCK-006](DOCK-006-systemd-docker-units.md)
**Blocks:** _(none)_

---

## Context

The ROADMAP specifies that `matrix install` should detect Docker availability and offer the user a choice between container-based and native (bare-metal) installation. Currently, `matrix install` only supports native installation with venv setup, systemd unit installation, and dependency compilation.

This ticket adds Docker detection logic and a branching install flow. When Docker is available, the user is prompted to choose their deployment mode. The Docker path installs the `ledmatrix-docker.service` unit and skips venv/dependency compilation. The native path continues as before.

---

## Acceptance Criteria

- [ ] `matrix install` detects whether Docker and Docker Compose are available
- [ ] User is prompted to choose: "Container (Docker)" or "Native (bare-metal)"
- [ ] If Docker is not available, native install proceeds automatically (no prompt)
- [ ] Docker install path: builds image, installs `ledmatrix-docker.service`, enables it
- [ ] Docker install path skips venv creation and pip dependency compilation
- [ ] Native install path remains unchanged
- [ ] Choice is logged and stored in config for future reference

---

## Implementation Checklist

### 1. Add Docker detection to install flow

- [ ] In `matrix install`, after initial checks, call `_is_docker_available()` (from DOCK-005)
- [ ] If Docker is available, prompt user with `click.confirm()` or `click.prompt()`:
  ```
  Docker detected. Install as a Docker container? (recommended)
  [1] Container (Docker) - runs in Docker, easy updates
  [2] Native (bare-metal) - traditional install, direct hardware access
  ```
- [ ] If Docker is not available, skip prompt and proceed with native install

### 2. Implement Docker install branch

- [ ] Build the Docker image: `docker compose build`
- [ ] Copy and configure `systemd/ledmatrix-docker.service`:
  - [ ] Replace `__PROJECT_ROOT_DIR__` with actual project root
  - [ ] Copy to `/etc/systemd/system/ledmatrix-docker.service`
- [ ] Run `systemctl daemon-reload`
- [ ] Enable and start the service: `systemctl enable --now ledmatrix-docker.service`
- [ ] Disable native units if they exist: `ledmatrix.service`, `ledmatrix-web.service`

### 3. Store deployment mode in config

- [ ] Write `deployment_mode: "docker"` or `deployment_mode: "native"` to config
- [ ] Future `matrix` CLI commands can check this to decide behavior

### 4. Add tests

- [ ] Add tests to `test/test_matrix_cli_docker.py` (or new file)
- [ ] Test Docker detection prompts with mocked `shutil.which`
- [ ] Test that Docker install branch calls correct subprocess commands
- [ ] Test that native install branch is unchanged
- [ ] Mock ALL filesystem and subprocess operations

### 5. Commit

```bash
git add scripts/matrix_cli.py test/test_matrix_cli_docker.py
git commit -m "feat(cli): add Docker detection and container install path to matrix install"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Syntax check
python3 -c "import ast; ast.parse(open('scripts/matrix_cli.py').read()); print('OK: syntax valid')"

# 2. Docker detection in install flow
grep -q "docker" scripts/matrix_cli.py && echo "OK: docker referenced in CLI"
grep -q "deployment_mode" scripts/matrix_cli.py && echo "OK: deployment_mode referenced"

# 3. Tests pass
distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_matrix_cli_docker.py -q --override-ini="addopts="'
```

---

## Notes

- The Docker install flow must still run as root (for systemd operations), same as the native install.
- If a user switches from native to Docker (or vice versa), the old systemd units should be disabled but NOT removed. This allows switching back.
- The `deployment_mode` config value is informational. It does NOT gate functionality -- users can still run `matrix docker start` even with `deployment_mode: "native"`.
- Test safety is critical: mock `subprocess.run`, `shutil.copy`, `Path.write_text`, and any systemctl calls. Do NOT touch real systemd units in tests.
- The `click.prompt()` with choices is preferred over `click.confirm()` for the two-option selection.
