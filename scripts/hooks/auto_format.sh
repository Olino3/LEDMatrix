#!/usr/bin/env bash
# PostToolUse hook: auto-format Python files with ruff after Edit/Write
# Called by Claude Code after Edit/Write on .py files

file="$TOOL_INPUT_file_path"

# Only format Python files
if [[ ! "$file" =~ \.py$ ]]; then
  exit 0
fi

# Resolve the repo root dynamically from the file path or git
REPO_ROOT=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null) \
  || REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
  echo "[auto_format] Could not determine repo root — skipping format." >&2
  exit 0
fi

cd "$REPO_ROOT"
uv run ruff format --quiet "$file" 2>/dev/null
uv run ruff check --fix --quiet "$file" 2>/dev/null
exit 0
