# SPIKE-017 -- `matrix uninstall`: Replace `uninstall.sh` with CLI Subcommand

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** _(none)_

---

## Context

`scripts/install/uninstall.sh` (170 lines) reverses the installation by stopping services, removing systemd units, cleaning up cache directories, and optionally removing the venv. This should be a `matrix uninstall` subcommand for consistency with `matrix install`.

---

## Scripts to Replace

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/install/uninstall.sh` | 170 | Full uninstall: stop services, remove units, clean cache | `matrix uninstall` |
| `scripts/install/debug_install.sh` | 62 | Debug install with verbose logging | `matrix install --full --verbose` (SPIKE-012) |

---

## Acceptance Criteria

- [ ] `matrix uninstall` subcommand exists with the following options:
  - `--keep-config` -- preserve config/config.json and config/config_secrets.json
  - `--keep-plugins` -- preserve plugins/ directory
  - `--keep-venv` -- preserve .venv/ directory
  - `--yes` / `-y` -- skip confirmation prompt
  - Default (no flags) removes everything except config and plugins
  - `--all` removes everything including config and plugins
- [ ] Uninstall steps (all idempotent):
  1. Stop and disable systemd services (ledmatrix, ledmatrix-web, ledmatrix-wifi-monitor)
  2. Remove systemd unit files
  3. Remove sudoers file (`/etc/sudoers.d/ledmatrix_web`)
  4. Remove cache directory (`/var/cache/ledmatrix`)
  5. Remove .venv/ (unless `--keep-venv`)
  6. Remove config files (unless `--keep-config`)
  7. Remove plugins/ (unless `--keep-plugins`)
  8. Remove ledmatrix group (if no members)
- [ ] Prints summary of what was removed
- [ ] Requires sudo (prompts if not root)
- [ ] `scripts/install/uninstall.sh` replaced with deprecation wrapper
- [ ] `scripts/install/debug_install.sh` replaced with deprecation wrapper pointing to `matrix install --full --verbose`

---

## Verification Steps

```bash
# 1. Uninstall help
matrix uninstall --help

# 2. Dry-run confirmation prompt
matrix uninstall 2>&1 | head -5

# 3. Deprecation wrapper
bash scripts/install/uninstall.sh 2>&1 | grep -i "deprecated\|matrix uninstall"
```

---

## Notes

- `matrix uninstall` is destructive. The default confirmation prompt should clearly list what will be removed.
- The `--keep-config` default is intentional -- users who reinstall usually want to keep their configuration.
- `debug_install.sh` is just `matrix install` with `set -x`. The `--verbose` flag on `matrix install` serves the same purpose.
