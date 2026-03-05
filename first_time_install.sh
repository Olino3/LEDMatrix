#!/bin/bash

# ============================================================================
# DEPRECATED — Use `matrix install` instead.
#
# This script has been replaced by the `matrix` CLI.
# See: https://github.com/ChuckBuilds/LEDMatrix#system-setup--installation
#
# To install LEDMatrix, run:
#   matrix install            # full install (venv + config + services)
#   matrix install --emulator # emulator/dev install (no systemd services)
#   matrix doctor             # verify installation health
#
# For Pi-specific hardware setup (rgbmatrix build, sound module config,
# performance tuning, WiFi monitor), see SPIKE-010 or run the individual
# scripts in scripts/install/ manually.
# ============================================================================

set -euo pipefail

echo ""
echo "=========================================="
echo "  DEPRECATED: first_time_install.sh"
echo "=========================================="
echo ""
echo "This script is deprecated and will be removed in a future release."
echo ""
echo "Please use the matrix CLI instead:"
echo "  matrix install            # full install (venv + config + services)"
echo "  matrix install --emulator # emulator/dev install"
echo "  matrix doctor             # verify installation health"
echo ""
echo "For more information, see the README:"
echo "  https://github.com/ChuckBuilds/LEDMatrix#system-setup--installation"
echo ""
echo "Forwarding to 'matrix install'..."
echo ""

# Resolve project root (where this script lives)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Forward to matrix install
exec python3 "$PROJECT_ROOT/scripts/matrix_cli.py" install "$@"
