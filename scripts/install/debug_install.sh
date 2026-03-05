#!/bin/bash
# Quick diagnostic script to check installation state
# Run this on the Pi: bash scripts/install/debug_install.sh
#
# NOTE: For comprehensive health checks, prefer: matrix doctor

echo "=== Diagnostic Script for Installation ==="
echo ""
echo "NOTE: For a full health check, run: matrix doctor"
echo ""

echo "1. Checking if running as root:"
if [ "$EUID" -eq 0 ]; then
    echo "   ✓ Running as root (EUID=$EUID)"
else
    echo "   ✗ NOT running as root (EUID=$EUID, user=$(whoami))"
fi
echo ""

echo "2. Checking for matrix CLI:"
if [ -f "./scripts/matrix_cli.py" ]; then
    echo "   ✓ Found ./scripts/matrix_cli.py"
else
    echo "   ✗ NOT found — ensure you are in the LEDMatrix project root"
    echo "   Current directory: $(pwd)"
fi
echo ""

echo "3. Checking uv installation:"
if command -v uv >/dev/null 2>&1; then
    echo "   ✓ uv is installed: $(which uv)"
else
    echo "   ✗ uv not found — install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

echo "4. Checking .venv:"
if [ -f ".venv/bin/python3" ]; then
    echo "   ✓ .venv exists"
    .venv/bin/python3 --version 2>/dev/null || echo "   ✗ Python in venv not working"
else
    echo "   ✗ .venv not found — run: matrix setup"
fi
echo ""

echo "5. Checking /tmp permissions:"
echo "   /tmp is writable: $([ -w /tmp ] && echo 'YES' || echo 'NO')"
echo "   /tmp permissions: $(stat -c '%a' /tmp 2>/dev/null || echo 'unknown')"
echo "   TMPDIR: ${TMPDIR:-not set}"
echo ""

echo "6. Checking stdin/TTY:"
if [ -t 0 ]; then
    echo "   ✓ stdin is a TTY (interactive)"
else
    echo "   ✗ stdin is NOT a TTY (non-interactive/pipe)"
    echo "   This is expected when running via curl | bash"
fi
echo ""

echo "=== Diagnostic Complete ==="
echo "For full health check, run: matrix doctor"
