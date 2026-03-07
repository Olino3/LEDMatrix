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
| [SPIKE-003](SPIKE-003-monorepo-plugin-quickfixes-pr.md) | Open PR for monorepo `display_manager.matrix` fixes (20 plugins) | Open | FOUND-006 |
| [SPIKE-004](SPIKE-004-remove-deprecated-legacy-scripts.md) | Remove deprecated legacy shell scripts and clean up dead code | Done | FOUND-003 |
| [SPIKE-005](SPIKE-005-doctor-rgbmatrix-import-check.md) | Add `rgbmatrix` import check to `matrix doctor` | Done | FOUND-003 |
| [SPIKE-006](SPIKE-006-ruff-lint-cleanup.md) | Fix pre-existing ruff lint violations in `src/` | Done | FOUND-005 |
| [SPIKE-007](SPIKE-007-bandit-config.md) | Create `bandit.yaml` configuration for pre-commit | Done | FOUND-005 |
| [SPIKE-008](SPIKE-008-plugin-deps-venv-migration.md) | Plugin dependency installation: migrate to venv | Done | FOUND-002 |
| [SPIKE-009](SPIKE-009-retire-first-time-install-script.md) | Retire `first_time_install.sh` in favor of `matrix install` | Done | FOUND-003, SPIKE-004 |
| [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md) | Expand `matrix install` with Pi-specific setup steps | Open | SPIKE-009 |
| [SPIKE-011](SPIKE-011-install-hardware-flag.md) | `matrix install --hardware` for rgbmatrix C-extension build | Open | SPIKE-005, SPIKE-009 |
| [SPIKE-012](SPIKE-012-matrix-install-full-oneshot.md) | `matrix install --full`: one-shot Pi installation | Open | SPIKE-010, SPIKE-011 |
| [SPIKE-013](SPIKE-013-matrix-cli-replace-diagnostic-scripts.md) | Replace diagnostic scripts with `matrix` CLI subcommands | Open | FOUND-003 |
| [SPIKE-014](SPIKE-014-matrix-cli-replace-fix-perms-scripts.md) | Replace permission/utility scripts with `matrix` CLI subcommands | Open | FOUND-003 |
| [SPIKE-015](SPIKE-015-matrix-cli-replace-network-scripts.md) | Replace network/WiFi scripts with `matrix` CLI subcommands | Open | FOUND-003 |
| [SPIKE-016](SPIKE-016-matrix-doctor-full-validation.md) | `matrix doctor`: full installation validation | Open | SPIKE-012, SPIKE-013 |
| [SPIKE-017](SPIKE-017-matrix-uninstall-subcommand.md) | `matrix uninstall`: replace `uninstall.sh` with CLI subcommand | Open | FOUND-003 |
| [SPIKE-018](SPIKE-018-archive-obsolete-scripts.md) | Archive obsolete shell scripts | Open | SPIKE-012, SPIKE-013, SPIKE-014, SPIKE-015, SPIKE-017 |
| [SPIKE-019](SPIKE-019-plugin-pyproject-toml.md) | Migrate plugin `requirements.txt` to per-plugin `pyproject.toml` | Open | SPIKE-008 |

## Status Summary

| Status | Count | Tickets |
|---|---|---|
| Done | 13 | FOUND-001 through FOUND-006, SPIKE-001, SPIKE-002, SPIKE-004 through SPIKE-009 |
| Open | 12 | SPIKE-003, SPIKE-010 through SPIKE-019 |
| In Progress | 0 | -- |
| Blocked | 0 | -- |

## Dependency Graph

```
FOUND-001 (pyproject.toml + uv) [Done]
  +-- FOUND-002 (venv bootstrap) [Done]
  |     +-- FOUND-003 (matrix CLI install/doctor) [Done]
  |     |     +-- SPIKE-004 (remove deprecated scripts) [Done]
  |     |     |     +-- SPIKE-009 (retire first_time_install.sh) [Done]
  |     |     |           +-- SPIKE-010 (expand matrix install -- Pi setup) [Open]
  |     |     |                 +-- SPIKE-012 (matrix install --full) [Open]
  |     |     |                       +-- SPIKE-016 (matrix doctor full validation) [Open]
  |     |     |                       +-- SPIKE-018 (archive obsolete scripts) [Open]
  |     |     +-- SPIKE-005 (doctor rgbmatrix import check) [Done]
  |     |     |     +-- SPIKE-011 (matrix install --hardware) [Open]
  |     |     |           +-- SPIKE-012 (matrix install --full) [Open]
  |     |     +-- SPIKE-013 (replace diagnostic scripts) [Open]
  |     |     |     +-- SPIKE-016 (matrix doctor full validation) [Open]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Open]
  |     |     +-- SPIKE-014 (replace fix-perms/utility scripts) [Open]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Open]
  |     |     +-- SPIKE-015 (replace network/WiFi scripts) [Open]
  |     |     |     +-- SPIKE-018 (archive obsolete scripts) [Open]
  |     |     +-- SPIKE-017 (matrix uninstall) [Open]
  |     |           +-- SPIKE-018 (archive obsolete scripts) [Open]
  |     +-- SPIKE-008 (plugin deps venv migration) [Done]
  |           +-- SPIKE-019 (plugin pyproject.toml migration) [Open]
  +-- FOUND-004 (CI pipeline) [Done]
  |     +-- FOUND-005 (pre-commit ruff) [Done]
  |           +-- SPIKE-006 (ruff lint cleanup) [Done]
  |           +-- SPIKE-007 (bandit config) [Done]
  +-- SPIKE-001 (update diagnostic scripts) [Done]
  +-- SPIKE-002 (update docs for uv) [Done]

FOUND-006 (plugin quick-fixes) [Done]
  +-- SPIKE-003 (monorepo PR -- 20 plugins, external repo) [Open]
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

### Core Phase 1 (3 open tickets)

These are the remaining tickets from the original sprint scope:

- **SPIKE-003** -- Monorepo PR for 20 plugins (requires push access to `ledmatrix-plugins` external repo)
- **SPIKE-008** -- Migrate plugin dependency installation to venv-aware commands
- **SPIKE-010** -- Expand `matrix install` with Pi-specific setup steps (apt, rgbmatrix, permissions, WiFi, sound, perf)

### CLI Consolidation (8 new tickets)

These tickets implement the ROADMAP goal of making `matrix` CLI the single entry point, replacing all 33 bash scripts:

- **SPIKE-011** -- `matrix install --hardware` for rgbmatrix C-extension build
- **SPIKE-012** -- `matrix install --full` one-shot Pi installation (absorbs install scripts)
- **SPIKE-013** -- Replace diagnostic scripts with `matrix diagnose` subcommands
- **SPIKE-014** -- Replace permission/utility scripts with `matrix fix` / `matrix clean` subcommands
- **SPIKE-015** -- Replace network/WiFi scripts with `matrix network` subcommands
- **SPIKE-016** -- Extend `matrix doctor` to full installation validation
- **SPIKE-017** -- `matrix uninstall` subcommand (replaces `uninstall.sh`)
- **SPIKE-018** -- Archive all obsolete scripts to `scripts/archive/`

### Recommended execution order

1. SPIKE-003 (external repo, no code dependencies)
2. SPIKE-008 (foundational for plugin ecosystem)
3. SPIKE-010 + SPIKE-011 (expand install capabilities)
4. SPIKE-013 + SPIKE-014 + SPIKE-015 + SPIKE-017 (can be parallelized)
5. SPIKE-012 (depends on SPIKE-010 + SPIKE-011)
6. SPIKE-016 (depends on SPIKE-012 + SPIKE-013)
7. SPIKE-018 (final cleanup, depends on all above)
