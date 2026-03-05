# SPIKE-014 -- Replace Permission and Utility Scripts with `matrix` CLI Subcommands

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** _(none)_

---

## Context

The project contains 12 utility and permission-fixing shell scripts in `scripts/fix_perms/`, `scripts/utils/`, and `scripts/` root. These handle permission repairs, cache cleanup, dependency markers, and plugin management tasks. They should be absorbed into the `matrix` CLI for a single entry point.

---

## Scripts to Replace

### Permission scripts -> `matrix fix permissions`

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/fix_perms/fix_assets_permissions.sh` | 137 | Fix sports logo/asset permissions | `matrix fix permissions --assets` |
| `scripts/fix_perms/fix_cache_permissions.sh` | 86 | Fix cache dir permissions | `matrix fix permissions --cache` |
| `scripts/fix_perms/fix_nhl_cache.sh` | 21 | Fix NHL cache specifically | Merge into `--cache` |
| `scripts/fix_perms/fix_plugin_permissions.sh` | 93 | Fix plugin dir permissions | `matrix fix permissions --plugins` |
| `scripts/fix_perms/fix_web_permissions.sh` | 105 | Fix web interface permissions | `matrix fix permissions --web` |
| `scripts/fix_perms/safe_plugin_rm.sh` | 61 | Safely remove plugin with perms | `matrix plugin uninstall` (already exists) |

### Utility scripts -> various `matrix` subcommands

| Script | Lines | Current Purpose | Proposed CLI Equivalent |
|--------|-------|----------------|------------------------|
| `scripts/utils/cleanup_venv.sh` | 23 | Remove old venv_web_v2 dir | Obsolete -- `venv_web_v2` is legacy. Archive script. |
| `scripts/utils/clear_python_cache.sh` | 20 | Clear __pycache__ dirs | `matrix clean cache` |
| `scripts/clear_dependency_markers.sh` | 29 | Clear plugin .dependencies_installed markers | `matrix clean deps` or `matrix plugin clean` |
| `scripts/remove_plugin_backups.sh` | 117 | Remove plugin backup dirs | `matrix plugin clean --backups` |
| `scripts/install_plugin_dependencies.sh` | 111 | Install plugin deps via pip | Superseded by SPIKE-008 (venv migration) |
| `scripts/download_pixlet.sh` | 139 | Download Pixlet binaries | `matrix setup pixlet` (niche; low priority) |

---

## Acceptance Criteria

- [ ] `matrix fix` subcommand group created with:
  - `matrix fix permissions` -- runs all permission fixes (equivalent to running all `fix_perms/*.sh`)
  - `matrix fix permissions --assets` / `--cache` / `--plugins` / `--web` for targeted fixes
- [ ] `matrix clean` subcommand group created with:
  - `matrix clean cache` -- clears `__pycache__`, `.pyc`, Flask cache
  - `matrix clean deps` -- clears `.dependencies_installed` markers
  - `matrix clean backups` -- removes plugin backup directories
- [ ] Each replaced script gets a deprecation wrapper
- [ ] `scripts/utils/cleanup_venv.sh` archived (references `venv_web_v2` which no longer exists)
- [ ] Permission fixes are idempotent and report what they changed

---

## Verification Steps

```bash
# 1. Fix permissions subcommand exists
matrix fix --help
matrix fix permissions --help

# 2. Clean subcommand exists
matrix clean --help
matrix clean cache --help

# 3. Deprecation wrappers
bash scripts/fix_perms/fix_cache_permissions.sh 2>&1 | grep -i "deprecated\|matrix fix"
```

---

## Notes

- Permission scripts require `sudo` on Pi. The `matrix fix permissions` command should detect if running without root and prompt for sudo.
- `safe_plugin_rm.sh` is already covered by `matrix plugin uninstall`. Can be archived directly.
- `download_pixlet.sh` is niche (Pixlet is an optional tool for Tidbyt-style apps). Low priority for CLI absorption; consider archiving instead.
