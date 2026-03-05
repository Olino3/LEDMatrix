# SPIKE-018 -- Archive Obsolete Shell Scripts

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Cleanup
**Depends on:** [SPIKE-012](SPIKE-012-matrix-install-full-oneshot.md), [SPIKE-013](SPIKE-013-matrix-cli-replace-diagnostic-scripts.md), [SPIKE-014](SPIKE-014-matrix-cli-replace-fix-perms-scripts.md), [SPIKE-015](SPIKE-015-matrix-cli-replace-network-scripts.md), [SPIKE-017](SPIKE-017-matrix-uninstall-subcommand.md)
**Blocks:** _(none)_

---

## Context

Once SPIKE-012 through SPIKE-017 are complete, all bash scripts in `scripts/` will either be:
1. Replaced by `matrix` CLI subcommands (with deprecation wrappers), or
2. Retained because they serve a unique purpose not covered by the CLI

This ticket performs the final cleanup: moving deprecated scripts to `scripts/archive/` and ensuring the `scripts/` directory only contains actively-used scripts.

---

## Script Disposition

### Archive (replaced by CLI)

These scripts will have been replaced by SPIKE-012 through SPIKE-017. Move to `scripts/archive/`.

| Script | Replaced By |
|--------|------------|
| `scripts/diagnose_dependencies.sh` | `matrix doctor` |
| `scripts/diagnose_web_interface.sh` | `matrix diagnose web` |
| `scripts/diagnose_web_ui.sh` | `matrix diagnose web` |
| `scripts/diagnose_plugin_permissions.sh` | `matrix doctor` / `matrix fix permissions` |
| `scripts/check_system_compatibility.sh` | `matrix doctor` |
| `scripts/verify_installation.sh` | `matrix doctor` |
| `scripts/verify_web_ui.sh` | `matrix diagnose web` |
| `scripts/verify_wifi_setup.sh` | `matrix diagnose network` |
| `scripts/verify_wifi_before_testing.sh` | `matrix diagnose network` |
| `scripts/emergency_reconnect.sh` | `matrix network reconnect` |
| `scripts/fix_internet_connectivity.sh` | `matrix network reconnect` |
| `scripts/test_captive_portal.sh` | `matrix network test-portal` |
| `scripts/troubleshoot_captive_portal.sh` | `matrix diagnose network` |
| `scripts/clear_dependency_markers.sh` | `matrix clean deps` |
| `scripts/remove_plugin_backups.sh` | `matrix clean backups` |
| `scripts/install_plugin_dependencies.sh` | SPIKE-008 / `matrix plugin install` |
| `scripts/fix_perms/fix_assets_permissions.sh` | `matrix fix permissions` |
| `scripts/fix_perms/fix_cache_permissions.sh` | `matrix fix permissions` |
| `scripts/fix_perms/fix_nhl_cache.sh` | `matrix fix permissions` |
| `scripts/fix_perms/fix_plugin_permissions.sh` | `matrix fix permissions` |
| `scripts/fix_perms/fix_web_permissions.sh` | `matrix fix permissions` |
| `scripts/fix_perms/safe_plugin_rm.sh` | `matrix plugin uninstall` |
| `scripts/utils/cleanup_venv.sh` | Obsolete (references venv_web_v2) |
| `scripts/utils/clear_python_cache.sh` | `matrix clean cache` |
| `scripts/install/uninstall.sh` | `matrix uninstall` |
| `scripts/install/debug_install.sh` | `matrix install --full --verbose` |
| `scripts/install/configure_wifi_permissions.sh` | `matrix install --full` |
| `scripts/install/configure_web_sudo.sh` | `matrix install --full` |
| `scripts/install/setup_cache.sh` | `matrix install --full` |
| `scripts/install/migrate_config.sh` | `matrix install --full` |

### Retain (still needed)

| Script | Reason |
|--------|--------|
| `scripts/matrix_cli.py` | The CLI itself |
| `scripts/render_plugin.py` | Used by `matrix plugin render` |
| `scripts/dev/dev_plugin_setup.sh` | Used by `matrix plugin link/unlink/status` |
| `scripts/dev/run_emulator.sh` | Thin wrapper; used by docs; harmless to keep |
| `scripts/install/install_service.sh` | Called by `matrix install`; keep until logic fully absorbed |
| `scripts/install/install_web_service.sh` | Called by `matrix install`; keep until logic fully absorbed |
| `scripts/install/install_wifi_monitor.sh` | Called by `matrix install --full`; keep until absorbed |
| `scripts/install/one-shot-install.sh` | Bootstrap script for curl-pipe-bash pattern; must remain |
| `scripts/download_pixlet.sh` | Niche tool; low priority; keep for now |

---

## Acceptance Criteria

- [ ] `scripts/archive/` directory created
- [ ] All archived scripts moved with a `git mv` to preserve history
- [ ] Each archived script has a header comment noting what replaced it
- [ ] `scripts/install/README.md` updated to reflect the new structure
- [ ] No remaining scripts in `scripts/` reference deleted file paths
- [ ] `matrix --help` output is the canonical reference for all available commands

---

## Notes

- This is the final cleanup ticket. It should only be executed after all SPIKE-012 through SPIKE-017 are Done.
- Use `git mv` (not `mv`) to preserve git history for the archived files.
- The `scripts/archive/` directory should have a README explaining that these are deprecated scripts preserved for reference.
