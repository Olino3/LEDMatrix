# SPIKE-001 — Update Diagnostic Scripts for `uv` Migration

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** [FOUND-001](FOUND-001-pyproject-uv-migration.md)
**Blocks:** _(none)_

---

## Context

After FOUND-001, the three `requirements*.txt` files have been removed in favor of `pyproject.toml` + `uv.lock`. Several diagnostic and utility shell scripts still reference these deleted files. They degrade gracefully (their `[ -f ... ]` guards cause them to skip), but the dependency-checking logic they contain is now useless.

---

## Affected Files

| File | What It Does | Lines Affected |
|------|-------------|----------------|
| `scripts/diagnose_dependencies.sh` | Reads `requirements.txt` line-by-line to verify each package is installed via `pip show` | ~85-188 |
| `scripts/diagnose_web_ui.sh` | Checks for `web_interface/requirements.txt` existence and verifies web deps are installed | ~87, 156-165 |
| `scripts/diagnose_web_interface.sh` | Checks for `web_interface/requirements.txt` existence | ~65 |
| `scripts/install/uninstall.sh` | Reads `requirements.txt` to build a list of packages for removal | ~126-141 |

---

## Acceptance Criteria

- [x] `scripts/diagnose_dependencies.sh` uses `uv pip list` or `uv tree` (or reads from `pyproject.toml`) instead of parsing `requirements.txt`
- [x] `scripts/diagnose_web_ui.sh` checks that `pyproject.toml` exists instead of `web_interface/requirements.txt`
- [x] `scripts/diagnose_web_interface.sh` updated similarly
- [x] `scripts/install/uninstall.sh` uses `uv pip list --format=freeze` or similar to determine installed packages for removal
- [x] All four scripts still function correctly when `.venv/` exists (normal case)
- [x] All four scripts produce a clear error message when `.venv/` does not exist

---

## Notes

- These scripts are not critical-path — they are developer/diagnostic tools. The fix is straightforward but was out of scope for FOUND-001 to keep the migration focused.
- Consider whether `matrix doctor` (FOUND-003) will make some of these scripts redundant.
