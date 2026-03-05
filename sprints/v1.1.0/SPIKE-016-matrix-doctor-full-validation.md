# SPIKE-016 -- `matrix doctor`: Full Installation Validation

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [SPIKE-012](SPIKE-012-matrix-install-full-oneshot.md), [SPIKE-013](SPIKE-013-matrix-cli-replace-diagnostic-scripts.md)
**Blocks:** _(none)_

---

## Context

`matrix doctor` currently checks 8 health items (uv, venv/Pillow, config files, plugins dir, systemd services, hardware, rgbmatrix, Python version). After SPIKE-012 implements `matrix install --full`, the doctor command needs to validate every step that the installer performs.

This ticket extends `matrix doctor` to be the definitive "is my installation healthy?" command -- replacing `scripts/verify_installation.sh` (221 lines) and `scripts/check_system_compatibility.sh` (293 lines).

---

## Acceptance Criteria

- [ ] `matrix doctor` checks all of the following (new checks marked with *):
  - uv installed (existing)
  - .venv exists and Pillow imports (existing)
  - config/config.json exists (existing)
  - config/config_secrets.json exists (existing)
  - plugins/ directory (existing)
  - systemd services (existing)
  - Hardware / emulator detection (existing)
  - rgbmatrix import on Pi (existing)
  - Python version (existing)
  - * All pyproject.toml dependencies importable
  - * Cache directory (`/var/cache/ledmatrix`) exists with correct permissions
  - * Web interface reachable on port 5000 (if service active)
  - * Sound module blacklisted (Pi only)
  - * Performance tuning applied -- `isolcpus` in `/boot/cmdline.txt` (Pi only)
  - * No conflicting services running (bluetooth, triggerhappy, pigpio)
  - * Plugin dependencies installed for all enabled plugins
  - * Config file valid JSON and passes schema validation
  - * Disk space adequate (warn below 500MB, fail below 100MB)
  - * Git repo clean / on expected branch (informational, not fail)
- [ ] `--quick` flag runs only the existing 9 checks (fast path for CI)
- [ ] `--verbose` / `-v` flag shows detailed output for each check
- [ ] `--json` flag outputs results as JSON (for programmatic consumption)
- [ ] Exit code 0 = all pass, 1 = any fail, 2 = only warnings
- [ ] Replaces `scripts/verify_installation.sh` and `scripts/check_system_compatibility.sh`

---

## Verification Steps

```bash
# 1. Full doctor check
EMULATOR=true matrix doctor

# 2. Quick mode
EMULATOR=true matrix doctor --quick

# 3. JSON output
EMULATOR=true matrix doctor --json | python3 -m json.tool

# 4. Verbose mode
EMULATOR=true matrix doctor -v
```

---

## Notes

- New checks should be non-blocking on dev machines (warn instead of fail for Pi-specific items when EMULATOR is set).
- The JSON output mode is useful for CI pipelines and monitoring.
- Consider grouping checks into categories in the output table: "Core", "Services", "Hardware", "Permissions".
