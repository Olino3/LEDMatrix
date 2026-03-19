# Archived Scripts

These shell scripts have been replaced by `matrix` CLI subcommands as part of the v1.1.0 Foundation sprint.

They are preserved here for reference only. Do not use them — use the CLI instead:

| Old Script | Replacement |
|------------|-------------|
| diagnose_*.sh, verify_*.sh, check_system_compatibility.sh | `matrix diagnose` / `matrix doctor` |
| fix_perms/*.sh | `matrix fix permissions` |
| emergency_reconnect.sh, fix_internet_connectivity.sh | `matrix network reconnect` |
| test_captive_portal.sh, troubleshoot_captive_portal.sh | `matrix network test-portal` / `matrix diagnose network` |
| clear_dependency_markers.sh | `matrix clean deps` |
| remove_plugin_backups.sh | `matrix clean backups` |
| clear_python_cache.sh | `matrix clean cache` |
| install_plugin_dependencies.sh | `matrix plugin install` |
| uninstall.sh | `matrix uninstall` |
| configure_web_sudo.sh, setup_cache.sh, configure_wifi_permissions.sh | `matrix install --full` |
| migrate_config.sh | `matrix install` |
| debug_install.sh | `matrix install --full` |
| cleanup_venv.sh | Obsolete (referenced removed venv_web_v2) |
| safe_plugin_rm.sh | `matrix plugin uninstall` |

Run `matrix --help` for the full list of available commands.
