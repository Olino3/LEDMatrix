# Sprint v1.1.0 -- Foundation

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
| [SPIKE-003](SPIKE-003-monorepo-plugin-quickfixes-pr.md) | Open PR for monorepo `display_manager.matrix` fixes (20 plugins) | Done | FOUND-006 |
| [SPIKE-004](SPIKE-004-remove-deprecated-legacy-scripts.md) | Remove deprecated legacy shell scripts and clean up dead code | Done | FOUND-003 |
| [SPIKE-005](SPIKE-005-doctor-rgbmatrix-import-check.md) | Add `rgbmatrix` import check to `matrix doctor` | Done | FOUND-003 |
| [SPIKE-006](SPIKE-006-ruff-lint-cleanup.md) | Fix pre-existing ruff lint violations in `src/` | Done | FOUND-005 |
| [SPIKE-007](SPIKE-007-bandit-config.md) | Create `bandit.yaml` configuration for pre-commit | Done | FOUND-005 |
| [SPIKE-008](SPIKE-008-plugin-deps-venv-migration.md) | Plugin dependency installation: migrate to venv | Done | FOUND-002 |
| [SPIKE-009](SPIKE-009-retire-first-time-install-script.md) | Retire `first_time_install.sh` in favor of `matrix install` | Done | FOUND-003, SPIKE-004 |
| [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md) | Expand `matrix install` with Pi-specific setup steps | Done | SPIKE-009 |
| [SPIKE-011](SPIKE-011-install-hardware-flag.md) | `matrix install --hardware` for rgbmatrix C-extension build | Done | SPIKE-005, SPIKE-009 |
| [SPIKE-012](SPIKE-012-matrix-install-full-oneshot.md) | `matrix install --full`: one-shot Pi installation | Done | SPIKE-010, SPIKE-011 |
| [SPIKE-013](SPIKE-013-matrix-cli-replace-diagnostic-scripts.md) | Replace diagnostic scripts with `matrix` CLI subcommands | Done | FOUND-003 |
| [SPIKE-014](SPIKE-014-matrix-cli-replace-fix-perms-scripts.md) | Replace permission/utility scripts with `matrix` CLI subcommands | Done | FOUND-003 |
| [SPIKE-015](SPIKE-015-matrix-cli-replace-network-scripts.md) | Replace network/WiFi scripts with `matrix` CLI subcommands | Done | FOUND-003 |
| [SPIKE-016](SPIKE-016-matrix-doctor-full-validation.md) | `matrix doctor`: full installation validation | Done | SPIKE-012, SPIKE-013 |
| [SPIKE-017](SPIKE-017-matrix-uninstall-subcommand.md) | `matrix uninstall`: replace `uninstall.sh` with CLI subcommand | Done | FOUND-003 |
| [SPIKE-018](SPIKE-018-archive-obsolete-scripts.md) | Archive obsolete shell scripts | Done | SPIKE-012, SPIKE-013, SPIKE-014, SPIKE-015, SPIKE-017 |
| [SPIKE-019](SPIKE-019-plugin-pyproject-toml.md) | Migrate plugin `requirements.txt` to per-plugin `pyproject.toml` | Done | SPIKE-008 |

## Status Summary

| Status | Count | Tickets |
|---|---|---|
| Done | 25 | All tickets |
| Open | 0 | -- |
| In Progress | 0 | -- |
| Blocked | 0 | -- |

## Dependency Graph

```
FOUND-001 (pyproject.toml + uv) [Done]
  +-- FOUND-002 (venv bootstrap) [Done]
  |     +-- FOUND-003 (matrix CLI install/doctor) [Done]
  |     |     +-- SPIKE-004 (remove deprecated scripts) [Done]
  |     |     |     +-- SPIKE-009 (retire first_time_install.sh) [Done]
  |     |     |           +-- SPIKE-010 (expand matrix install -- Pi setup) [Done]
  |     |     |                 +-- SPIKE-012 (matrix install --full) [Done]
  |     |     |                       +-- SPIKE-016 (matrix doctor full validation) [Done]
  |     |     |                       +-- SPIKE-018 (archive obsolete scripts) [Done]
  |     |     +-- SPIKE-005 (doctor rgbmatrix import check) [Done]
  |     |     |     +-- SPIKE-011 (matrix install --hardware) [Done]
  |     |     |           +-- SPIKE-012 (matrix install --full) [Done]
  |     |     +-- SPIKE-013 (replace diagnostic scripts) [Done]
  |     |     |     +-- SPIKE-016 (matrix doctor full validation) [Done]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Done]
  |     |     +-- SPIKE-014 (replace fix-perms/utility scripts) [Done]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Done]
  |     |     +-- SPIKE-015 (replace network/WiFi scripts) [Done]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Done]
  |     |     +-- SPIKE-017 (matrix uninstall) [Done]
  |     |           +-- SPIKE-018 (archive obsolete scripts) [Done]
  |     +-- SPIKE-008 (plugin deps venv migration) [Done]
  |           +-- SPIKE-019 (plugin pyproject.toml migration) [Done]
  +-- FOUND-004 (CI pipeline) [Done]
  |     +-- FOUND-005 (pre-commit ruff) [Done]
  |           +-- SPIKE-006 (ruff lint cleanup) [Done]
  |           +-- SPIKE-007 (bandit config) [Done]
  +-- SPIKE-001 (update diagnostic scripts) [Done]
  +-- SPIKE-002 (update docs for uv) [Done]

FOUND-006 (plugin quick-fixes) [Done]
  +-- SPIKE-003 (monorepo PR -- 20 plugins, external repo) [Done]
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

## Sprint Complete

All 25 tickets (6 FOUND + 19 SPIKE) are done. The `matrix` CLI is now the single entry point for all LEDMatrix operations.

### Notes
- **SPIKE-003**: PR opened at https://github.com/Olino3/ledmatrix-plugins/pull/1 (completed via Olino3 fork)
- **SPIKE-019**: Research-only spike; recommendation doc at `docs/plans/2026-03-19-spike-019-plugin-pyproject-toml.md`
- **Tests**: New test files need validation once dev environment has `python3-devel` installed
- 30 deprecated scripts archived to `scripts/archive/` with deprecation wrappers
