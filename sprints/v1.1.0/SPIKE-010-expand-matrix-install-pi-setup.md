# SPIKE-010 — Expand `matrix install` with Pi-Specific Setup Steps

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Spike / Enhancement
**Depends on:** [SPIKE-009](SPIKE-009-retire-first-time-install-script.md)
**Blocks:** _(none)_

---

## Context

SPIKE-009 replaced `first_time_install.sh` with a thin deprecation wrapper that delegates to `matrix install`. However, `matrix install` currently only handles three steps:

1. Sync the `.venv` via `uv sync`
2. Create `config/config.json` from template
3. Install systemd services (via `install_service.sh`)

The original `first_time_install.sh` handled ~19 additional Pi-specific setup steps that are not yet absorbed into `matrix install`. Users performing a fresh Raspberry Pi installation will need to run individual scripts manually until this work is complete.

---

## Gap Analysis

The following `first_time_install.sh` functionality is **NOT** covered by `matrix install`:

### System Prerequisites
- [ ] OS validation (Raspberry Pi OS Lite, Debian 13/Trixie, no desktop)
- [ ] Network connectivity check
- [ ] `apt` package installation (python3-pip, python3-venv, build-essential, cython3, scons, cmake, etc.)

### Hardware Setup
- [ ] Git submodule init for `rpi-rgb-led-matrix-master`
- [ ] Build and install `rgbmatrix` Python bindings
- [ ] Python capabilities for hardware timing (`cap_sys_nice` via `setcap`)
- [ ] Sound module blacklisting (`snd_bcm2835`)
- [ ] Performance tuning (`isolcpus=3` in cmdline.txt, `dtparam=audio=off`)
- [ ] Removal of conflicting services (bluetooth, triggerhappy, pigpio)

### Permissions & Security
- [ ] Cache directory setup (`/var/cache/ledmatrix` with `ledmatrix` group)
- [ ] Assets directory permissions (sports logos, etc.)
- [ ] Plugin and plugin-repos directory permissions
- [ ] Config directory permissions (`config_secrets.json` with 640)
- [ ] Passwordless sudo for web interface (`/etc/sudoers.d/ledmatrix_web`)
- [ ] User group membership (`systemd-journal`, `adm`, `ledmatrix`)

### Services
- [ ] Web service installation (`install_web_service.sh`)
- [ ] WiFi monitor service installation (`install_wifi_monitor.sh`)
- [ ] Systemd unit file permission hardening
- [ ] WiFi management permissions (PolicyKit)

### Post-Install
- [ ] Installation verification tests
- [ ] Network diagnostics / IP address display
- [ ] Reboot prompt

---

## Proposed Approach

Expand `matrix install` with optional flags or sub-steps:

```
matrix install               # current behavior (venv + config + services)
matrix install --full        # full Pi setup (apt, rgbmatrix, permissions, etc.)
matrix install --hardware    # build rgbmatrix from source
matrix install --permissions # fix all file/directory permissions
```

Alternatively, create focused subcommands:
```
matrix setup                 # venv only (already exists)
matrix install               # venv + config + services (already exists)
matrix install --full        # everything including Pi-specific steps
matrix doctor                # verify health (already exists)
```

---

## Notes

- The individual install scripts in `scripts/install/` still work and can be run manually
- `one-shot-install.sh` now calls `matrix install` directly
- Some steps (apt packages, rgbmatrix build) require `sudo` and real Pi hardware
- Consider making Pi-specific steps no-op on non-Pi platforms (dev machines)
- This is a natural follow-up to SPIKE-009 and can be done incrementally
