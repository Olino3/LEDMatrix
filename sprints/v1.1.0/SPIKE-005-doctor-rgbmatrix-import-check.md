# SPIKE-005 — Add `rgbmatrix` Import Check to `matrix doctor`

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Spike / Enhancement
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** _(none)_

---

## Context

The `matrix doctor` command (added in FOUND-003) checks for `.venv`, `uv`, config files, systemd services, and hardware detection. However, it does not verify that the `rgbmatrix` Python module can actually be imported.

On Raspberry Pi hardware, `rgbmatrix` is built from source (C extension from `rpi-rgb-led-matrix`). If it's missing, the display will fail to start. `matrix doctor` should warn about this when running on Pi hardware (i.e., when `/dev/mem` exists and `EMULATOR` is not set).

Additionally, `matrix install` could optionally support a `--hardware` flag that triggers the `rgbmatrix` C-extension build from source, replacing the manual steps currently documented in `first_time_install.sh`.

---

## Acceptance Criteria

- [x] `matrix doctor` attempts `import rgbmatrix` inside the `.venv` Python and reports WARN if it fails on Pi hardware
- [x] On emulator/dev machines, the missing `rgbmatrix` is not flagged (since `RGBMatrixEmulator` is used instead)
- [x] Consider adding `matrix install --hardware` to automate the `rgbmatrix` C-extension build (requires `apt` packages and compilation — evaluate feasibility)

---

## Notes

- The `rgbmatrix` C-extension build is complex and hardware-specific. Automating it carries risk — evaluate whether a guided wizard or just a doctor warning is the better approach.
- `pyproject.toml` documents that `rpi-rgb-led-matrix` can be pip-installed from `git+https://github.com/hzeller/rpi-rgb-led-matrix`. This may be a simpler path than building from source.

---

## Implementation Summary

### Doctor check (implemented)

Added an `rgbmatrix` import check to `matrix doctor` in `scripts/matrix_cli.py`. The check:
- Only runs on Pi hardware (`/dev/mem` exists) when `EMULATOR` is not set and `.venv` exists
- Runs `import rgbmatrix` inside the `.venv` Python via `subprocess.run`
- Reports **PASS** ("C extension importable") if the import succeeds
- Reports **WARN** ("Not installed — display will fail without EMULATOR=true") if it fails
- Is completely skipped on emulator/dev machines

### `matrix install --hardware` feasibility evaluation

**Recommendation: defer to a follow-up ticket (SPIKE-010).**

Findings:
1. `pyproject.toml` already has an empty `[project.optional-dependencies] hardware` group, but the `rpi-rgb-led-matrix` package cannot be added as a direct dependency because it fails resolution on non-ARM platforms.
2. The simplest automated path is: `uv pip install git+https://github.com/hzeller/rpi-rgb-led-matrix` — this builds from source and requires `gcc`, `python3-dev`, and other apt packages to be present.
3. A `--hardware` flag on `matrix install` would need to:
   - Detect ARM architecture
   - Ensure C build tools are installed (`sudo apt install -y python3-dev gcc make`)
   - Run `uv pip install git+https://github.com/hzeller/rpi-rgb-led-matrix` inside the venv
   - Handle build failures gracefully with clear error messages
4. This is feasible but carries risk (C compilation errors, platform-specific issues). A better UX approach may be a guided "wizard" that checks prerequisites before attempting the build.
5. This work overlaps with SPIKE-009 (retire `first_time_install.sh`), which also covers hardware setup automation.

**Conclusion:** The doctor warning implemented here provides immediate value. The `--hardware` automation should be tackled alongside SPIKE-009 in a dedicated ticket.
