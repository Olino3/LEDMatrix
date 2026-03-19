#!/bin/bash
# DEPRECATED: This script is deprecated in favor of the Python-based PluginLoader.
#
# Plugin dependencies are now installed automatically at plugin load time via
# `uv pip install` (with pip fallback) targeting the project venv.
#
# If you need to manually install plugin dependencies, use:
#
#   .venv/bin/python3 -c "
#   from src.plugin_system.dep_installer import install_plugin_dependencies
#   from pathlib import Path
#   install_plugin_dependencies(Path('plugins/<plugin-id>/requirements.txt'))
#   "
#
# Or simply restart the display service — dependencies install on boot:
#
#   sudo systemctl restart ledmatrix
#
# This wrapper will be removed in a future release.

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠  DEPRECATED: This script is deprecated.${NC}"
echo ""
echo "Plugin dependencies are now installed automatically by the PluginLoader"
echo "using 'uv pip install' (with pip fallback) targeting the project venv."
echo ""
echo "To install all plugin dependencies, simply restart the display service:"
echo "  sudo systemctl restart ledmatrix"
echo ""
echo "Or use the Python-based installer directly:"
echo '  .venv/bin/python3 -c "'
echo '  from src.plugin_system.dep_installer import install_plugin_dependencies'
echo '  from pathlib import Path'
echo "  install_plugin_dependencies(Path('plugins/<plugin-id>/requirements.txt'))"
echo '  "'
echo ""

# Still run for backwards compat, but via uv/venv
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LEDMATRIX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGINS_DIR="$LEDMATRIX_DIR/plugins"

if [ ! -d "$PLUGINS_DIR" ]; then
    echo -e "${RED}Error: Plugins directory not found at $PLUGINS_DIR${NC}"
    exit 1
fi

# Prefer uv, fall back to pip
if command -v uv &> /dev/null; then
    INSTALL_CMD="uv pip install"
elif [ -f "$LEDMATRIX_DIR/.venv/bin/python3" ]; then
    INSTALL_CMD="$LEDMATRIX_DIR/.venv/bin/python3 -m pip install"
else
    INSTALL_CMD="pip3 install"
fi

echo "Using: $INSTALL_CMD"
echo ""

for plugin_dir in "$PLUGINS_DIR"/*/ ; do
    if [ -d "$plugin_dir" ]; then
        requirements_file="$plugin_dir/requirements.txt"
        if [ -f "$requirements_file" ] && [ -s "$requirements_file" ]; then
            plugin_name=$(basename "$plugin_dir")
            echo "Installing dependencies for $plugin_name..."
            $INSTALL_CMD -r "$requirements_file" || echo -e "${RED}Failed: $plugin_name${NC}"
        fi
    fi
done

echo ""
echo "Done. Consider using 'sudo systemctl restart ledmatrix' instead in the future."
