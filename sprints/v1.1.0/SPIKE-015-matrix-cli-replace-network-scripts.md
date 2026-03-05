# SPIKE-015 -- Replace Network and WiFi Scripts with `matrix` CLI Subcommands

**Status:** Open
**Phase:** v1.1.0 -- Foundation
**Type:** Spike / Enhancement
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** _(none)_

---

## Context

The project contains 5 network/WiFi-related shell scripts that handle emergency reconnection, captive portal testing, and connectivity fixes. These are Pi-specific operational scripts. They should either be absorbed into the `matrix` CLI or archived if they serve edge-case scenarios that are better documented than automated.

---

## Scripts to Evaluate

| Script | Lines | Current Purpose | Recommendation |
|--------|-------|----------------|----------------|
| `scripts/emergency_reconnect.sh` | 111 | Emergency WiFi reconnection after captive portal failure | `matrix network reconnect` |
| `scripts/fix_internet_connectivity.sh` | 109 | Fix internet after AP mode testing | Merge with `matrix network reconnect` |
| `scripts/test_captive_portal.sh` | 149 | Test captive portal functionality | `matrix network test-portal` (dev/debug only) |
| `scripts/troubleshoot_captive_portal.sh` | 120 | Troubleshoot captive portal WiFi | `matrix diagnose network` (from SPIKE-013) |
| `scripts/install/configure_wifi_permissions.sh` | 152 | Set up PolicyKit WiFi permissions | Absorbed into `matrix install --full` (SPIKE-012) |

---

## Acceptance Criteria

- [ ] `matrix network` subcommand group created with:
  - `matrix network reconnect` -- emergency WiFi reconnection (combines `emergency_reconnect.sh` and `fix_internet_connectivity.sh`)
  - `matrix network test-portal` -- captive portal testing (wraps `test_captive_portal.sh` logic)
  - `matrix network status` -- show current connectivity, IP addresses, WiFi signal strength
- [ ] `scripts/install/configure_wifi_permissions.sh` absorbed into `matrix install --full` (SPIKE-012)
- [ ] `scripts/troubleshoot_captive_portal.sh` replaced by `matrix diagnose network` (SPIKE-013)
- [ ] Each replaced script gets a deprecation wrapper
- [ ] All network commands detect non-Pi platforms and exit gracefully

---

## Verification Steps

```bash
# 1. Network subcommand exists
matrix network --help

# 2. Status works on any platform
matrix network status

# 3. Pi-only commands exit gracefully on dev machines
matrix network reconnect 2>&1 | grep -i "pi\|hardware\|not supported"
```

---

## Notes

- Network scripts are inherently Pi-specific (they use `nmcli`, `wpa_supplicant`, `hostapd`). On non-Pi platforms, these commands should print a message and exit 0.
- The captive portal feature is a WiFi setup wizard for headless Pi. It is rarely used after initial setup. Consider whether `matrix network test-portal` is worth implementing or whether documentation is sufficient.
- `emergency_reconnect.sh` and `fix_internet_connectivity.sh` have significant overlap. Consolidate into one `matrix network reconnect` command.
