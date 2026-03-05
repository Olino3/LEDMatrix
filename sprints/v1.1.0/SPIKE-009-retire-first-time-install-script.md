# SPIKE-009 — Retire `first_time_install.sh` in Favor of `matrix install`

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike / Cleanup
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md), [SPIKE-004](SPIKE-004-remove-deprecated-legacy-scripts.md)
**Blocks:** _(none)_

---

## Context

SPIKE-004 removed the deprecated shell scripts (`start_display.sh`, `stop_display.sh`, `web_interface/run.sh`) and cleaned up the dead `requirements.txt` code paths in `first_time_install.sh`. However, `first_time_install.sh` itself is still a ~700-line script that largely overlaps with `matrix install`.

The ROADMAP lists fully retiring `first_time_install.sh` as a goal. Several docs still reference it as the primary installation method.

---

## Acceptance Criteria

- [ ] Evaluate whether `matrix install` fully covers all functionality in `first_time_install.sh`
- [ ] Either replace `first_time_install.sh` with a thin wrapper that calls `matrix install`, or remove it entirely
- [ ] Update `README.md` installation section to recommend `matrix install` instead of `first_time_install.sh`
- [ ] Update `docs/SSH_UNAVAILABLE_AFTER_INSTALL.md` references
- [ ] Update `docs/DEVELOPMENT.md` references
- [ ] Update `docs/PLUGIN_DEPENDENCY_GUIDE.md` references
- [ ] Update `scripts/install/README.md` references
- [ ] Update `ROADMAP.md` to reflect completion

---

## Files Referencing `first_time_install.sh`

- `README.md` (lines 340-346) — primary install instructions
- `docs/SSH_UNAVAILABLE_AFTER_INSTALL.md` (lines 5, 97)
- `docs/DEVELOPMENT.md` (line 55)
- `docs/PLUGIN_DEPENDENCY_GUIDE.md` (line 232)
- `scripts/install/README.md` (line 25)
- `ROADMAP.md` (lines 27-28)
- Various sprint docs (contextual references)

---

## Notes

- This is out-of-scope cleanup discovered during SPIKE-004.
- Before removing the script, verify that `matrix install` handles all installation steps: OS checks, apt packages, Python install, rgbmatrix build, config setup, and service installation.
- Consider adding a deprecation warning to `first_time_install.sh` as an interim step (similar to what was done for the other scripts before SPIKE-004 removed them).
