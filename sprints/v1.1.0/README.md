# Sprint v1.1.0 — Foundation

**Goal:** Python modernization, developer tooling, and CI infrastructure. No breaking changes to public APIs or behavior.

**ROADMAP phase:** Phase 1

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [FOUND-001](FOUND-001-pyproject-uv-migration.md) | Migrate to `pyproject.toml` + `uv` | Done | — |
| [FOUND-002](FOUND-002-venv-bootstrap.md) | Virtual environment bootstrap everywhere | Done | FOUND-001 |
| [FOUND-003](FOUND-003-matrix-cli-install-doctor.md) | `matrix` CLI — `install`, `setup`, and `doctor` commands | Open | FOUND-001, FOUND-002 |
| [FOUND-004](FOUND-004-ci-pipeline.md) | GitHub Actions CI pipeline | Open | FOUND-001 |
| [FOUND-005](FOUND-005-precommit-ruff.md) | Migrate pre-commit hooks to `ruff` | Open | FOUND-004 |
| [FOUND-006](FOUND-006-plugin-quickfixes.md) | Plugin quick-fixes: `matrix.width` / `matrix.height` refs | Open | — |
| [SPIKE-001](SPIKE-001-update-diagnostic-scripts.md) | Update diagnostic scripts for `uv` migration | Done | FOUND-001 |
| [SPIKE-002](SPIKE-002-update-docs-for-uv-migration.md) | Update documentation for `uv` migration | Done | FOUND-001 |
| [SPIKE-003](SPIKE-003-plugin-deps-venv-migration.md) | Plugin dependency installation: migrate to venv | Open | FOUND-002 |

## Dependency Graph

```
FOUND-001 (pyproject.toml)
  ├── FOUND-002 (venv bootstrap)
  │     └── FOUND-003 (matrix CLI install/doctor)
  └── FOUND-004 (CI pipeline)
        └── FOUND-005 (pre-commit ruff)

FOUND-006 (plugin quick-fixes)   ← independent
```

## Definition of Done (Phase 1)

- [ ] Single `pyproject.toml` at repo root; all three `requirements*.txt` files removed
- [ ] `uv.lock` committed; `uv sync` is the only install command needed
- [ ] All systemd service files boot from `.venv/bin/python3`
- [ ] `matrix install`, `matrix setup`, `matrix doctor` commands functional
- [ ] Root-level `first_time_install.sh`, `start_display.sh`, `stop_display.sh`, `web_interface/run.sh` deprecated (warning added) or removed
- [ ] GitHub Actions CI passes on Python 3.10, 3.11, and 3.12: lint, types, tests, audit
- [ ] Pre-commit hooks use `ruff check` + `ruff format` (flake8 removed)
- [ ] `football-scoreboard` and `hockey-scoreboard` plugin versions bumped, `plugins.json` regenerated
