#!/bin/bash
# Diagnostic script for Python dependency installation issues
# Run this if pip gets stuck on "Preparing metadata (pyproject.toml)"

set -e

echo "=========================================="
echo "LEDMatrix Dependency Diagnostic Tool"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root (parent of scripts/ directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project directory: $PROJECT_ROOT_DIR"
echo ""

# Check system resources
echo "=== System Resources ==="
echo "Disk space:"
df -h / | tail -1
echo ""
echo "Memory:"
free -h
echo ""
echo "CPU info:"
grep -E "^model name|^Hardware|^Revision" /proc/cpuinfo | head -3 || echo "CPU info not available"
echo ""

# Check for .venv
echo "=== Virtual Environment ==="
VENV_DIR="$PROJECT_ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✓${NC} .venv/ directory exists"
    if [ -x "$VENV_PYTHON" ]; then
        echo -e "${GREEN}✓${NC} .venv/bin/python3 is executable"
    else
        echo -e "${RED}✗${NC} .venv/bin/python3 not found or not executable"
        echo "  Run: uv sync"
    fi
else
    echo -e "${RED}✗${NC} .venv/ directory not found at $VENV_DIR"
    echo "  Run: uv sync   (this will create the venv and install all dependencies)"
fi
echo ""

# Check Python and uv versions
echo "=== Python Environment ==="
echo "Python version:"
if [ -x "$VENV_PYTHON" ]; then
    echo "  venv: $($VENV_PYTHON --version)"
fi
python3 --version 2>/dev/null && echo "  system: $(python3 --version)" || true
echo ""
echo "uv version:"
if command -v uv >/dev/null 2>&1; then
    uv --version
else
    echo -e "${RED}✗${NC} uv not found"
    echo "  Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

# Check if timeout command is available
echo "=== Available Tools ==="
if command -v timeout >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} timeout command available"
else
    echo -e "${YELLOW}⚠${NC} timeout command not available (install with: sudo apt install coreutils)"
fi

if command -v apt >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} apt available"
else
    echo -e "${RED}✗${NC} apt not available"
fi
echo ""

# Check installed build tools
echo "=== Build Tools ==="
BUILD_TOOLS=("gcc" "g++" "make" "python3-dev" "build-essential" "cython3")
for tool in "${BUILD_TOOLS[@]}"; do
    if dpkg -l | grep -q "^ii.*$tool"; then
        echo -e "${GREEN}✓${NC} $tool installed"
    else
        echo -e "${RED}✗${NC} $tool not installed"
    fi
done
echo ""

# Check uv cache
echo "=== uv Cache ==="
if command -v uv >/dev/null 2>&1; then
    UV_CACHE_DIR=$(uv cache dir 2>/dev/null || echo "unknown")
    echo "uv cache directory: $UV_CACHE_DIR"
    if [ -d "$UV_CACHE_DIR" ]; then
        CACHE_SIZE=$(du -sh "$UV_CACHE_DIR" 2>/dev/null | cut -f1 || echo "unknown")
        echo "Cache size: $CACHE_SIZE"
        echo "You can clear the cache with: uv cache clean"
    fi
else
    echo -e "${YELLOW}⚠${NC} uv not installed — cache check skipped"
fi
echo ""

# Check pyproject.toml
echo "=== Project Configuration ==="
if [ -f "$PROJECT_ROOT_DIR/pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml found"
    TOTAL_DEPS=$(grep -E '^\s+"[a-zA-Z]' "$PROJECT_ROOT_DIR/pyproject.toml" | wc -l)
    echo "Approximate dependency count: $TOTAL_DEPS"
    echo ""
    echo "Packages that may need building from source:"
    grep -E '^\s+"(numpy|freetype|cython|scipy|pandas)' "$PROJECT_ROOT_DIR/pyproject.toml" || echo "  (none detected)"
else
    echo -e "${RED}✗${NC} pyproject.toml not found at $PROJECT_ROOT_DIR/pyproject.toml"
fi
if [ -f "$PROJECT_ROOT_DIR/uv.lock" ]; then
    echo -e "${GREEN}✓${NC} uv.lock found"
else
    echo -e "${YELLOW}⚠${NC} uv.lock not found — run: uv sync"
fi
echo ""

# Test uv sync
echo "=== Test Installation ==="
if command -v uv >/dev/null 2>&1; then
    echo "Testing uv with a dry-run sync..."
    if uv sync --project "$PROJECT_ROOT_DIR" --dry-run >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} uv sync dry-run succeeded"
    else
        echo -e "${RED}✗${NC} uv sync dry-run failed"
        echo "Try: uv sync --project $PROJECT_ROOT_DIR"
    fi
else
    echo -e "${RED}✗${NC} uv not installed — cannot test dependency resolution"
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

# Check for common issues
echo "=== Common Issues Check ==="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLON}⚠${NC} Running as root - ensure --break-system-packages flag is used"
else
    echo -e "${GREEN}✓${NC} Not running as root (good for user installs)"
fi

# Check network connectivity
if ping -c 1 -W 3 pypi.org >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Network connectivity to PyPI OK"
else
    echo -e "${RED}✗${NC} Cannot reach pypi.org - check network connection"
fi

# Check for proxy issues
if [ -n "${HTTP_PROXY:-}" ] || [ -n "${HTTPS_PROXY:-}" ]; then
    echo -e "${BLUE}ℹ${NC} Proxy configured: HTTP_PROXY=${HTTP_PROXY:-none}, HTTPS_PROXY=${HTTPS_PROXY:-none}"
else
    echo -e "${GREEN}✓${NC} No proxy configured"
fi
echo ""

# Recommendations
echo "=== Recommendations ==="
echo ""
echo "If dependency installation fails:"
echo ""
echo "1. Install uv (if not installed):"
echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
echo ""
echo "2. Create/sync the virtual environment:"
echo "   uv sync"
echo ""
echo "3. Install build tools (needed for packages that compile from source):"
echo "   sudo apt update && sudo apt install -y build-essential python3-dev cython3"
echo ""
echo "4. Reinstall with verbose output if sync fails:"
echo "   uv sync -v"
echo ""
echo "5. Clear uv cache if corrupted:"
echo "   uv cache clean"
echo ""
echo "6. Check disk space - building packages requires temporary space:"
echo "   df -h"
echo ""
echo "7. For slow builds, increase swap space:"
echo "   sudo dphys-swapfile swapoff"
echo "   sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048"
echo "   sudo dphys-swapfile setup"
echo "   sudo dphys-swapfile swapon"
echo ""

# Check which packages are already installed
echo "=== Currently Installed Packages ==="
if [ -d "$VENV_DIR" ] && command -v uv >/dev/null 2>&1; then
    echo "Packages installed in .venv (via uv pip list):"
    echo ""
    uv pip list --python "$VENV_PYTHON" 2>/dev/null || echo -e "${RED}✗${NC} Could not list packages from .venv"
elif [ -d "$VENV_DIR" ] && [ -x "$VENV_PYTHON" ]; then
    echo "Packages installed in .venv (via pip list):"
    echo ""
    "$VENV_PYTHON" -m pip list 2>/dev/null || echo -e "${RED}✗${NC} Could not list packages from .venv"
else
    echo -e "${RED}✗${NC} No .venv found — run 'uv sync' to create the virtual environment and install dependencies"
fi
echo ""

echo "=========================================="
echo "Diagnostic complete!"
echo "=========================================="

