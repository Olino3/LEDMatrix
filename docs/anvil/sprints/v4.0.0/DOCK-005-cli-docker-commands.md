# DOCK-005 — Matrix CLI Docker Command Group

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Feat
**Depends on:** [DOCK-003](DOCK-003-compose-production.md)
**Blocks:** [DOCK-007](DOCK-007-install-docker-detection.md)

---

## Context

The ROADMAP specifies five new CLI subcommands under `matrix docker`: `start`, `stop`, `logs`, `update`, and `build`. These commands wrap `docker compose` operations so users do not need to remember Compose file paths or flags.

The CLI is a single-file Click application at `scripts/matrix_cli.py` (~2900 lines). New command groups are added before the `# Entry point` section, following the existing pattern of section headers and helper functions.

---

## Acceptance Criteria

- [ ] `matrix docker` command group exists with a help message
- [ ] `matrix docker start` pulls (if needed) and starts containers via `docker compose up -d`
- [ ] `matrix docker stop` stops containers via `docker compose down`
- [ ] `matrix docker logs` tails container logs via `docker compose logs -f`
- [ ] `matrix docker update` pulls the latest image and restarts containers
- [ ] `matrix docker build` builds the image locally via `docker compose build`
- [ ] All commands detect if Docker/Docker Compose is not installed and exit gracefully
- [ ] Commands use the correct Compose file path relative to the project root

---

## Implementation Checklist

### 1. Add Docker detection helper

- [ ] Add `_is_docker_available()` helper function that checks for `docker` and `docker compose` in PATH
- [ ] Return a descriptive error message if Docker is not available

### 2. Create the `docker` command group

- [ ] Add `@cli.group()` for `docker` with help text: "Manage LEDMatrix Docker containers"
- [ ] Add section header comment: `# ---------------------------------------------------------------------------`

### 3. Implement `docker start`

- [ ] `@docker.command()` named `start`
- [ ] Option `--dev` flag to include `compose.dev.yml` overlay
- [ ] Check Docker availability, exit with error if not found
- [ ] Build the `docker compose` command with correct `-f` flags
- [ ] Run `docker compose up -d` (detached mode)
- [ ] Print status message on success

### 4. Implement `docker stop`

- [ ] `@docker.command()` named `stop`
- [ ] Run `docker compose down`
- [ ] Option `--volumes` flag to also remove named volumes (with confirmation)

### 5. Implement `docker logs`

- [ ] `@docker.command()` named `logs`
- [ ] Option `--service` to filter by service name (`display` or `web`)
- [ ] Option `--tail` with default 100 for number of lines
- [ ] Run `docker compose logs -f --tail N [service]`

### 6. Implement `docker update`

- [ ] `@docker.command()` named `update`
- [ ] Run `docker compose pull` to get latest images
- [ ] Run `docker compose up -d` to restart with new images
- [ ] Print before/after image digest for verification

### 7. Implement `docker build`

- [ ] `@docker.command()` named `build`
- [ ] Option `--no-cache` flag
- [ ] Run `docker compose build [--no-cache]`

### 8. Add tests

- [ ] Create `test/test_matrix_cli_docker.py`
- [ ] Test that `docker` group and all subcommands are registered
- [ ] Test `_is_docker_available()` with mocked `shutil.which`
- [ ] Test that commands exit gracefully when Docker is not available
- [ ] Mock all `subprocess.run` calls -- do NOT actually run Docker commands in tests

### 9. Commit

```bash
git add scripts/matrix_cli.py test/test_matrix_cli_docker.py
git commit -m "feat(cli): add matrix docker command group for container management"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Syntax check (no distrobox needed)
python3 -c "import ast; ast.parse(open('scripts/matrix_cli.py').read()); print('OK: syntax valid')"

# 2. Docker group registered
grep -q "def docker" scripts/matrix_cli.py && echo "OK: docker group defined"

# 3. All subcommands defined
grep -q "def start" scripts/matrix_cli.py && echo "OK: start command"
grep -q "def stop" scripts/matrix_cli.py && echo "OK: stop command"
grep -q "def logs" scripts/matrix_cli.py && echo "OK: logs command"
grep -q "def update" scripts/matrix_cli.py && echo "OK: update command"
grep -q "def build" scripts/matrix_cli.py && echo "OK: build command"

# 4. Test file exists
test -f test/test_matrix_cli_docker.py && echo "OK: test file exists"

# 5. Tests pass (distrobox)
distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_matrix_cli_docker.py -q --override-ini="addopts="'
```

---

## Notes

- Follow the existing CLI pattern: use `_run()` helper for subprocess calls, `console` for Rich output, `LEDMATRIX_ROOT` for project path resolution.
- The `--dev` flag on `docker start` adds `-f compose.dev.yml` to the Compose command. This is the primary way developers will run in emulator mode.
- All `docker compose` commands must be run from the project root directory (where `compose.yml` lives). Use `LEDMATRIX_ROOT` to ensure correct working directory.
- The `logs` command should use `subprocess.run` with `stdin=sys.stdin` to allow Ctrl+C to stop tailing.
- Do NOT add container health checks in this ticket -- that is Phase 5 (Observability) work.
- Test safety: mock all subprocess calls. Do NOT run actual Docker commands in tests.
