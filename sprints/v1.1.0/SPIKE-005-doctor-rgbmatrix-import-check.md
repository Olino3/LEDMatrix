# SPIKE-005 — Add `rgbmatrix` Import Check to `matrix doctor`

**Status:** Open
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

- [ ] `matrix doctor` attempts `import rgbmatrix` inside the `.venv` Python and reports WARN if it fails on Pi hardware
- [ ] On emulator/dev machines, the missing `rgbmatrix` is not flagged (since `RGBMatrixEmulator` is used instead)
- [ ] Consider adding `matrix install --hardware` to automate the `rgbmatrix` C-extension build (requires `apt` packages and compilation — evaluate feasibility)

---

## Notes

- The `rgbmatrix` C-extension build is complex and hardware-specific. Automating it carries risk — evaluate whether a guided wizard or just a doctor warning is the better approach.
- `pyproject.toml` documents that `rpi-rgb-led-matrix` can be pip-installed from `git+https://github.com/hzeller/rpi-rgb-led-matrix`. This may be a simpler path than building from source.
