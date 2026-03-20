#!/usr/bin/env bash
# run_frontend_dev.sh — Start FastAPI backend + Angular dev server together.
#
# FastAPI runs on port 5000, Angular dev server on port 4200.
# Angular proxies /api/v3 and /stream requests to FastAPI via proxy.conf.json.
#
# Usage:
#   bash scripts/dev/run_frontend_dev.sh
#
# Press Ctrl+C to stop both servers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FASTAPI_PID=""
NG_PID=""

cleanup() {
    echo ""
    echo "Stopping servers..."
    for pid in "${FASTAPI_PID:-}" "${NG_PID:-}"; do
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    echo "Done."
}
trap cleanup EXIT INT TERM

echo "Starting FastAPI backend on port 5000..."
cd "$PROJECT_ROOT"
EMULATOR=true python3 src/api/start.py &
FASTAPI_PID=$!

# Wait briefly for FastAPI to start
sleep 2

echo "Starting Angular dev server on port 4200..."
cd "$PROJECT_ROOT/frontend"
npx ng serve --open=false &
NG_PID=$!

echo ""
echo "=== Frontend Dev Environment ==="
echo "  Angular:  http://localhost:4200"
echo "  FastAPI:  http://localhost:5000"
echo "  API docs: http://localhost:5000/docs"
echo ""
echo "  Angular proxies /api/v3/* and /stream/* → FastAPI"
echo "  Press Ctrl+C to stop both servers."
echo "================================="
echo ""

wait
