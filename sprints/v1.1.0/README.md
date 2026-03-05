# Sprint v1.1.0 — Foundation

**Goal:** Python modernization, developer tooling, and CI infrastructure. No breaking changes to public APIs or behavior.

**ROADMAP phase:** Phase 1

---

## Tickets

| ID | Title | Status | Depends On |
|---|---|---|---|
| [FOUND-001](FOUND-001-pyproject-uv-migration.md) | Migrate to `pyproject.toml` + `uv` | Done | -- |
| [FOUND-002](FOUND-002-venv-bootstrap.md) | Virtual environment bootstrap everywhere | Done | FOUND-001 |
| [FOUND-003](FOUND-003-matrix-cli-install-doctor.md) | `matrix` CLI -- `install`, `setup`, and `doctor` commands | Done | FOUND-001, FOUND-002 |
| [FOUND-004](FOUND-004-ci-pipeline.md) | GitHub Actions CI pipeline | Done | FOUND-001 |
| [FOUND-005](FOUND-005-precommit-ruff.md) | Migrate pre-commit hooks to `ruff` | Done | FOUND-004 |
| [FOUND-006](FOUND-006-plugin-quickfixes.md) | Plugin quick-fixes: `matrix.width` / `matrix.height` refs | Done | -- |
| [SPIKE-001](SPIKE-001-update-diagnostic-scripts.md) | Update diagnostic scripts for `uv` migration | Done | FOUND-001 |
| [SPIKE-002](SPIKE-002-update-docs-for-uv-migration.md) | Update documentation for `uv` migration | Done | FOUND-001 |
| [SPIKE-003](SPIKE-003-monorepo-plugin-quickfixes-pr.md) | Open PR for monorepo `display_manager.matrix` fixes (20 plugins) | Open | FOUND-006 |
| [SPIKE-004](SPIKE-004-remove-deprecated-legacy-scripts.md) | Remove deprecated legacy shell scripts and clean up dead code | Done | FOUND-003 |
| [SPIKE-005](SPIKE-005-doctor-rgbmatrix-import-check.md) | Add `rgbmatrix` import check to `matrix doctor` | Done | FOUND-003 |
| [SPIKE-006](SPIKE-006-ruff-lint-cleanup.md) | Fix pre-existing ruff lint violations in `src/` | Done | FOUND-005 |
| [SPIKE-007](SPIKE-007-bandit-config.md) | Create or remove `bandit.yaml` configuration | Done | FOUND-005 |
| [SPIKE-008](SPIKE-008-plugin-deps-venv-migration.md) | Plugin dependency installation: migrate to venv | Open | FOUND-002 |
| [SPIKE-009](SPIKE-009-retire-first-time-install-script.md) | Retire `first_time_install.sh` in favor of `matrix install` | Done | FOUND-003, SPIKE-004 |
| [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md) | Expand `matrix install` with Pi-specific setup steps | Open | SPIKE-009 |
| [SPIKE-009](SPIKE-009-retire-first-time-install-script.md) | Retire `first_time_install.sh` in favor of `matrix install` | Open | FOUND-003, SPIKE-004 |
| [SPIKE-010](SPIKE-010-install-hardware-flag.md) | `matrix install --hardware` for rgbmatrix C-extension build | Open | SPIKE-005, SPIKE-009 |

## Dependency Graph

```
FOUND-001 (pyproject.toml + uv)
  ├── FOUND-002 (venv bootstrap)
  │     ├── FOUND-003 (matrix CLI install/doctor)
  │     │     ├── SPIKE-004 [Done] (remove deprecated scripts)
  │     │     │     └── SPIKE-009 [Done] (retire first_time_install.sh)
  │     │     │           └── SPIKE-010 [Open] (expand matrix install with Pi setup)
  │     │     ├── SPIKE-005 [Open] (doctor rgbmatrix import check)
  │     │     └── SPIKE-009 [Done] (retire first_time_install.sh) ← also depends on SPIKE-004
  │     │     │     └── SPIKE-009 [Open] (retire first_time_install.sh)
  │     │     ├── SPIKE-005 [Done] (doctor rgbmatrix import check)
  │     │     │     └── SPIKE-010 [Open] (matrix install --hardware) ← also depends on SPIKE-009
  │     │     └── SPIKE-009 [Open] (retire first_time_install.sh) ← also depends on SPIKE-004
  │     └── SPIKE-008 [Open] (plugin deps venv migration)
  ├── FOUND-004 (CI pipeline)
  │     └── FOUND-005 (pre-commit ruff)
  │           ├── SPIKE-006 [Done] (ruff lint cleanup)
  │           └── SPIKE-007 [Done] (bandit config)
  ├── SPIKE-001 [Done] (update diagnostic scripts)
  └── SPIKE-002 [Done] (update docs for uv)

FOUND-006 (plugin quick-fixes) [Done]
  └── SPIKE-003 [Open] (monorepo PR -- 20 plugins, external repo)
```

## Definition of Done (Phase 1)

- [x] Single `pyproject.toml` at repo root; all three `requirements*.txt` files removed
- [x] `uv.lock` committed; `uv sync` is the only install command needed
- [ ] All systemd service files boot from `.venv/bin/python3` (templates use placeholder; needs Pi deployment verification)
- [x] `matrix install`, `matrix setup`, `matrix doctor` commands functional
- [x] Root-level `start_display.sh`, `stop_display.sh`, `web_interface/run.sh` removed (SPIKE-004)
- [x] `first_time_install.sh` replaced with deprecation wrapper pointing to `matrix install` (SPIKE-009)
- [x] GitHub Actions CI passes on Python 3.10, 3.11, and 3.12: lint, types, tests, audit
- [x] Pre-commit hooks use `ruff check` + `ruff format` (flake8 removed)
- [x] `football-scoreboard` and `hockey-scoreboard` plugin versions bumped, `plugins.json` regenerated (FOUND-006 complete; 20 total plugins fixed -- see SPIKE-003 for monorepo PR)

## Remaining Work

5 tickets are still Open. All are spikes/cleanup discovered during implementation of the core FOUND tickets:

- **SPIKE-003** -- Monorepo PR for 20 plugins (requires push access to external repo)
- **SPIKE-007** -- Decide on bandit.yaml configuration
- **SPIKE-005** -- Enhance `matrix doctor` with rgbmatrix import check
- **SPIKE-008** -- Migrate plugin dependency installation to venv-aware commands
- **SPIKE-010** -- Expand `matrix install` with Pi-specific setup steps (apt, rgbmatrix, permissions, WiFi, sound, perf)
- **SPIKE-009** -- Fully retire `first_time_install.sh`
- **SPIKE-010** -- `matrix install --hardware` for rgbmatrix C-extension build (new, discovered during SPIKE-005)
