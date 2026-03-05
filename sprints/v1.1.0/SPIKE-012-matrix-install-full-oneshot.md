# SPIKE-012 -- `matrix install --full`: One-Shot Pi Installation

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [SPIKE-010](SPIKE-010-expand-matrix-install-pi-setup.md), [SPIKE-011](SPIKE-011-install-hardware-flag.md)
**Blocks:** [SPIKE-016](SPIKE-016-matrix-doctor-full-validation.md)

---

## Context

`matrix install` currently handles three steps: venv sync, config creation, and systemd service installation. The original `first_time_install.sh` handled ~19 additional Pi-specific steps. SPIKE-010 catalogued the gaps; this ticket implements the full one-shot install path.

The goal is that a user on a fresh Raspberry Pi can run a single command -- `matrix install --full` -- and have a fully working LEDMatrix installation with no manual steps required.

---

## Acceptance Criteria

- [ ] `matrix install --full` performs all steps in sequence, with progress reporting:
  1. OS validation (Raspberry Pi OS, Debian-based)
  2. Network connectivity check
  3. System package installation via `apt` (python3, python3-dev, build-essential, cython3, scons, cmake, git, curl)
  4. `uv` installation if not present
  5. Repository clone/update (if run from outside repo, skip; if inside repo, proceed)
  6. Venv creation via `uv sync`
  7. `rgbmatrix` C-extension build from source (delegates to `--hardware` logic from SPIKE-011)
  8. Config file creation from template
  9. Cache directory setup (`/var/cache/ledmatrix` with `ledmatrix` group)
  10. File permissions setup (config, assets, plugins)
  11. Sound module blacklisting (`snd_bcm2835`)
  12. Performance tuning (`isolcpus=3`, `dtparam=audio=off`)
  13. Conflicting service removal (bluetooth, triggerhappy, pigpio)
  14. Systemd service installation (display + web)
  15. WiFi monitor service installation
  16. Passwordless sudo for web interface
  17. Installation verification via `matrix doctor`
- [ ] Each step is idempotent -- safe to re-run after partial failure
- [ ] Each step prints clear pass/fail status with actionable error messages
- [ ] Steps requiring `sudo` prompt once at the start, not per-step
- [ ] Non-Pi platforms get a clear error message for hardware-specific steps
- [ ] `--skip-hardware` flag to skip rgbmatrix build and hardware tuning (for emulator-only installs on Pi)
- [ ] `--yes` / `-y` flag to skip all confirmation prompts

---

## Implementation Notes

The logic currently lives across these bash scripts, which should be absorbed:

| Script | Steps Absorbed |
|--------|---------------|
| `scripts/install/install_service.sh` | Systemd display service |
| `scripts/install/install_web_service.sh` | Systemd web service |
| `scripts/install/install_wifi_monitor.sh` | WiFi monitor service |
| `scripts/install/configure_wifi_permissions.sh` | PolicyKit WiFi permissions |
| `scripts/install/configure_web_sudo.sh` | Passwordless sudo for web |
| `scripts/install/setup_cache.sh` | Cache directory setup |
| `scripts/install/migrate_config.sh` | Config migration |
| `scripts/fix_perms/fix_*` | Permission fixes |

Each absorbed script should be reimplemented as a Python function in `matrix_cli.py` (or a helper module) rather than shelling out to bash. This ensures consistent error handling, progress reporting, and testability.

---

## Verification Steps

```bash
# 1. Help text shows --full flag
matrix install --help | grep -q "\-\-full" && echo "PASS" || echo "FAIL"

# 2. Dry-run on non-Pi aborts hardware steps gracefully
matrix install --full 2>&1 | grep -i "not.*raspberry\|not.*arm\|skipping.*hardware"

# 3. Full install on Pi completes successfully (requires Pi hardware)
# sudo matrix install --full -y

# 4. Doctor passes after full install
# matrix doctor
```

---

## Notes

- This is the largest SPIKE in the sprint. Consider splitting implementation across multiple PRs.
- The `one-shot-install.sh` script handles the "bootstrap from nothing" case (curl | bash). It should continue to exist as a thin wrapper that installs git + uv, clones the repo, then calls `matrix install --full`.
- Some steps (sound blacklisting, isolcpus) require a reboot. `matrix install --full` should print a reboot prompt at the end, not reboot automatically.
