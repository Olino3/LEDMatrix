#!/bin/bash

# LED Matrix Uninstall Script
# Reverses everything done by `matrix install` and the individual install scripts.
# Safe to run multiple times — skips steps that are already undone.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step()    { echo ""; echo -e "${BLUE}== $1 ==${NC}"; }
print_ok()      { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn()    { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_skip()    { echo -e "  ${YELLOW}-${NC} $1 (skipped — not found)"; }

# Must run as root (same as install scripts)
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo bash scripts/install/uninstall.sh${NC}"
    exit 1
fi

# Resolve project root (two levels up from scripts/install/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Determine the original non-root user
if [ -n "${SUDO_USER:-}" ]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER=$(logname 2>/dev/null || whoami)
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  LED Matrix Uninstaller${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "  Project root : $PROJECT_ROOT"
echo "  User         : $ACTUAL_USER"
echo ""

# ---------------------------------------------------------------------------
# Confirmation prompt
# ---------------------------------------------------------------------------
read -r -p "This will remove all LED Matrix services, system files, and optionally the project directory. Continue? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Stop and disable systemd services
# ---------------------------------------------------------------------------
print_step "Stopping and disabling systemd services"

SERVICES=(ledmatrix ledmatrix-web ledmatrix-wifi-monitor)
for SVC in "${SERVICES[@]}"; do
    SVC_FILE="/etc/systemd/system/${SVC}.service"
    if systemctl list-units --all --type=service 2>/dev/null | grep -q "${SVC}.service"; then
        systemctl stop    "${SVC}.service" 2>/dev/null && print_ok "Stopped ${SVC}.service"    || print_warn "Could not stop ${SVC}.service (may already be stopped)"
        systemctl disable "${SVC}.service" 2>/dev/null && print_ok "Disabled ${SVC}.service"   || print_warn "Could not disable ${SVC}.service"
    else
        print_skip "${SVC}.service"
    fi
    if [ -f "$SVC_FILE" ]; then
        rm -f "$SVC_FILE"
        print_ok "Removed $SVC_FILE"
    fi
done

systemctl daemon-reload
print_ok "systemd daemon reloaded"

# ---------------------------------------------------------------------------
# 2. Remove sudoers file
# ---------------------------------------------------------------------------
print_step "Removing sudoers configuration"

SUDOERS_FILE="/etc/sudoers.d/ledmatrix_web"
if [ -f "$SUDOERS_FILE" ]; then
    rm -f "$SUDOERS_FILE"
    print_ok "Removed $SUDOERS_FILE"
else
    print_skip "$SUDOERS_FILE"
fi

# ---------------------------------------------------------------------------
# 3. Remove cache directory
# ---------------------------------------------------------------------------
print_step "Removing cache directory"

CACHE_DIR="/var/cache/ledmatrix"
if [ -d "$CACHE_DIR" ]; then
    rm -rf "$CACHE_DIR"
    print_ok "Removed $CACHE_DIR"
else
    print_skip "$CACHE_DIR"
fi

# ---------------------------------------------------------------------------
# 4. Remove ledmatrix system group
# ---------------------------------------------------------------------------
print_step "Removing ledmatrix system group"

if getent group ledmatrix > /dev/null 2>&1; then
    # Remove users from the group first
    for U in $(getent group ledmatrix | cut -d: -f4 | tr ',' ' '); do
        gpasswd -d "$U" ledmatrix 2>/dev/null && print_ok "Removed $U from ledmatrix group" || true
    done
    groupdel ledmatrix && print_ok "Deleted ledmatrix group"
else
    print_skip "ledmatrix group"
fi

# ---------------------------------------------------------------------------
# 5. Remove Python virtual environment
# ---------------------------------------------------------------------------
print_step "Removing Python virtual environment"

VENV_DIR="$PROJECT_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
    read -r -p "  Remove .venv/ directory (all installed Python packages)? (y/N): " VENV_CONFIRM
    if [[ "$VENV_CONFIRM" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        print_ok "Removed $VENV_DIR"
    else
        print_skip ".venv/ directory (user declined)"
    fi
else
    print_skip ".venv/ directory"
fi

# ---------------------------------------------------------------------------
# 6. Remove project directory
# ---------------------------------------------------------------------------
print_step "Removing project directory"

echo "  Project directory: $PROJECT_ROOT"
read -r -p "  Delete the entire project directory (including config and plugins)? (y/N): " DIR_CONFIRM
if [[ "$DIR_CONFIRM" =~ ^[Yy]$ ]]; then
    # Step out of the directory first so we can delete it
    cd /tmp
    rm -rf "$PROJECT_ROOT"
    print_ok "Removed $PROJECT_ROOT"
else
    print_skip "Project directory (user declined)"
    echo ""
    echo "  The following were left in place:"
    echo "    $PROJECT_ROOT/config/config.json"
    echo "    $PROJECT_ROOT/config/config_secrets.json"
    echo "    $PROJECT_ROOT/plugins/"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Uninstall complete.${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "If you added your user to any groups during install, you may need to"
echo "log out and back in (or reboot) for those changes to fully take effect."
echo ""
