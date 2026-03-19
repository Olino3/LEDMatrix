#!/bin/bash
# LEDMatrix Emulator Runner
# This script runs the LEDMatrix system in emulator mode for development and testing

# Resolve project root (parent of scripts/dev/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

echo "Starting LEDMatrix Emulator..."
echo "Press Ctrl+C to stop"
echo ""

# Set emulator mode
export EMULATOR=true

# Run the main application using venv python
if [ -x "$VENV_PYTHON" ]; then
    cd "$PROJECT_ROOT" && exec "$VENV_PYTHON" run.py
else
    echo "Warning: .venv not found at ${VENV_PYTHON}, falling back to system python3"
    cd "$PROJECT_ROOT" && exec python3 run.py
fi
