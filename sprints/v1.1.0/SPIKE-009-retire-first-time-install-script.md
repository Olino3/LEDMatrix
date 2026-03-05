# SPIKE-009 — Retire `first_time_install.sh` in Favor of `matrix install`

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Spike / Cleanup
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md), [SPIKE-004](SPIKE-004-remove-deprecated-legacy-scripts.md)
**Blocks:** _(none)_

---

## Context

SPIKE-004 removed the deprecated shell scripts (`start_display.sh`, `stop_display.sh`, `web_interface/run.sh`) and cleaned up the dead `requirements.txt` code paths in `first_time_install.sh`. However, `first_time_install.sh` itself was still a ~700-line script that largely overlapped with `matrix install`.

The ROADMAP lists fully retiring `first_time_install.sh` as a goal. Several docs still referenced it as the primary installation method.

---

## Acceptance Criteria

- [x] Evaluate whether `matrix install` fully covers all functionality in `first_time_install.sh`
- [x] Either replace `first_time_install.sh` with a thin wrapper that calls `matrix install`, or remove it entirely
- [x] Update `README.md` installation section to recommend `matrix install` instead of `first_time_install.sh`
- [x] Update `docs/SSH_UNAVAILABLE_AFTER_INSTALL.md` references
- [x] Update `docs/DEVELOPMENT.md` references
- [x] Update `docs/PLUGIN_DEPENDENCY_GUIDE.md` references
- [x] Update `scripts/install/README.md` references
- [x] Update `ROADMAP.md` to reflect completion

---

## Evaluation Results

`matrix install` covers 3 of ~19 steps from `first_time_install.sh`:
1. Sync `.venv` via `uv sync`
2. Create `config/config.json` from template
3. Install systemd services (main display service only)

The remaining Pi-specific steps (apt packages, rgbmatrix build, permissions, WiFi, sound, performance tuning) are tracked in [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md).

## Implementation

- `first_time_install.sh` replaced with a thin deprecation wrapper (~40 lines) that prints a warning and forwards to `matrix install`
- `one-shot-install.sh` updated to call `matrix install` directly (also installs `uv` as prerequisite)
- `debug_install.sh` rewritten for the new `matrix install` workflow
- All documentation references updated across README, docs/, scripts/, ROADMAP, and .cursor rules
- Tests added in `test/test_first_time_install_deprecation.py`

## Follow-up

- [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md) — Expand `matrix install` with Pi-specific setup steps (apt, rgbmatrix, permissions, WiFi, sound, performance)

---

## Files Updated

- `first_time_install.sh` — replaced with deprecation wrapper
- `scripts/install/one-shot-install.sh` — uses `matrix install`
- `scripts/install/debug_install.sh` — rewritten
- `README.md` — manual install instructions
- `docs/SSH_UNAVAILABLE_AFTER_INSTALL.md`
- `docs/DEVELOPMENT.md`
- `docs/PLUGIN_DEPENDENCY_GUIDE.md`
- `scripts/install/README.md`
- `scripts/verify_installation.sh`
- `scripts/install/uninstall.sh`
- `scripts/install_dependencies_apt.py`
- `.cursor/rules/raspberry-pi-development.mdc`
- `ROADMAP.md`

---

## Notes

- This was out-of-scope cleanup discovered during SPIKE-004.
- The deprecation wrapper approach was chosen over full removal because `one-shot-install.sh` and existing users may still reference the script by name.
- Pi-specific hardware setup (rgbmatrix build, sound module, performance tuning) requires a future expansion of `matrix install` (SPIKE-010).
