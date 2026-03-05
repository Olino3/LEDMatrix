# SPIKE-011 -- `matrix install --hardware` for rgbmatrix C-extension Build

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [SPIKE-005](SPIKE-005-doctor-rgbmatrix-import-check.md), [SPIKE-009](SPIKE-009-retire-first-time-install-script.md)
**Blocks:** _(none)_

---

## Context

SPIKE-005 added an `rgbmatrix` import check to `matrix doctor`, which warns when the C extension is missing on Pi hardware. The next step is to automate the installation of the `rgbmatrix` C extension via `matrix install --hardware`.

This work was identified during SPIKE-005 evaluation and overlaps with SPIKE-009 (retiring `first_time_install.sh`), which also covers hardware setup automation.

---

## Acceptance Criteria

- [ ] `matrix install --hardware` detects ARM architecture and aborts with a clear message on non-Pi platforms
- [ ] Checks for required apt packages (`python3-dev`, `gcc`, `make`) and prompts to install if missing
- [ ] Runs `uv pip install git+https://github.com/hzeller/rpi-rgb-led-matrix` inside the `.venv`
- [ ] Handles build failures gracefully with actionable error messages
- [ ] `matrix doctor` confirms the installation succeeded after running `matrix install --hardware`

---

## Notes

- Previously tracked as SPIKE-010 (duplicate ID). Renumbered to SPIKE-011 during sprint cleanup.
- The `--hardware` flag already exists conceptually in `pyproject.toml`'s `[project.optional-dependencies] hardware` group (currently empty/commented).
- Consider a guided wizard approach that checks prerequisites before attempting the build, rather than failing mid-compilation.
- Coordinate with SPIKE-010 (expand matrix install) to avoid duplicating hardware setup logic.
