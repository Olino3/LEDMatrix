# SPIKE-013 -- Replace Diagnostic Shell Scripts with `matrix` CLI Subcommands

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** [SPIKE-016](SPIKE-016-matrix-doctor-full-validation.md)

---

## Context

The project contains 8 diagnostic and verification shell scripts that overlap with `matrix doctor` functionality or could be better served as `matrix` CLI subcommands. These scripts were useful before the CLI existed but are now fragmented entry points that confuse users and agents.

---

## Scripts to Replace

### Diagnostic scripts -> `matrix doctor` checks

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/diagnose_dependencies.sh` | 223 | Verify Python packages installed | `matrix doctor` already checks venv/Pillow; extend to check all deps |
| `scripts/diagnose_web_interface.sh` | 195 | Diagnose web UI issues | `matrix doctor --web` or `matrix diagnose web` |
| `scripts/diagnose_web_ui.sh` | 197 | Diagnose web UI startup | Merge with above (overlapping functionality) |
| `scripts/diagnose_plugin_permissions.sh` | 172 | Check plugin dir permissions | `matrix doctor` plugin check; extend with permission verification |
| `scripts/check_system_compatibility.sh` | 293 | OS version, Python, packages | `matrix doctor` already covers most of this |

### Verification scripts -> `matrix verify` or `matrix doctor`

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/verify_installation.sh` | 221 | Post-install verification | `matrix doctor` (already does this) |
| `scripts/verify_web_ui.sh` | 160 | Verify web UI running | `matrix doctor --web` |

### Network diagnostic scripts -> `matrix diagnose network`

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/verify_wifi_setup.sh` | 346 | WiFi health check | `matrix diagnose network` |
| `scripts/verify_wifi_before_testing.sh` | 225 | Pre-test WiFi check | `matrix diagnose network` |

---

## Acceptance Criteria

- [ ] `matrix doctor` extended with:
  - `--verbose` / `-v` flag for detailed output (replaces diagnose scripts' extra output)
  - Dependency completeness check (all pyproject.toml deps importable)
  - Web interface health check (port 5000 reachable, Flask responding)
  - Plugin directory permissions check
- [ ] `matrix diagnose` subcommand group created with:
  - `matrix diagnose web` -- full web interface diagnosis (replaces both `diagnose_web_*.sh`)
  - `matrix diagnose network` -- WiFi and connectivity checks (replaces `verify_wifi_*.sh`)
  - `matrix diagnose plugins` -- plugin permission and dependency checks
- [ ] Each replaced script gets a deprecation wrapper (one-liner pointing to CLI equivalent)
- [ ] All diagnostic output uses Rich tables/panels for consistent formatting

---

## Verification Steps

```bash
# 1. New diagnose subcommands exist
matrix diagnose --help
matrix diagnose web --help
matrix diagnose network --help
matrix diagnose plugins --help

# 2. Doctor verbose mode works
EMULATOR=true matrix doctor -v

# 3. Deprecation wrappers in place
bash scripts/diagnose_dependencies.sh 2>&1 | grep -i "deprecated\|matrix doctor"
```

---

## Notes

- Do not delete the original scripts immediately. Replace them with thin deprecation wrappers first. Actual removal in a follow-up.
- `matrix diagnose network` is only useful on Pi hardware. On dev machines, print a message and exit 0.
- The `check_system_compatibility.sh` script (293 lines) has the most overlap with `matrix doctor`. Most of its checks are already covered.
