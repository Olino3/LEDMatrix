#!/bin/bash
# ===========================================================================
# DEPRECATED — Use the Python-based PluginLoader instead.
#
# Plugin dependencies are now installed automatically at load time by
# src/plugin_system/plugin_loader.py using `uv pip install` (with a
# fallback to `pip install` when uv is not available).
#
# This script is retained only for backwards compatibility and will be
# removed in a future release.  If you need to manually reinstall plugin
# dependencies, run:
#
#   uv pip install -r plugins/<plugin-id>/requirements.txt
#
# See SPIKE-008 in sprints/v1.1.0/ for details.
# ===========================================================================

set -e

YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}⚠  DEPRECATED: This script is deprecated.${NC}"
echo -e "${YELLOW}   Plugin dependencies are now installed automatically by the PluginLoader.${NC}"
echo -e "${YELLOW}   To manually install a plugin's dependencies, run:${NC}"
echo -e "${YELLOW}     uv pip install -r plugins/<plugin-id>/requirements.txt${NC}"
echo ""
echo -e "${YELLOW}   This script will be removed in a future release.${NC}"
echo ""
