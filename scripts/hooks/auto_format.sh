#!/usr/bin/env bash
# PostToolUse hook: auto-format Python files with ruff after Edit/Write
# Called by Claude Code after Edit/Write on .py files

file="$TOOL_INPUT_file_path"

# Only format Python files
if [[ ! "$file" =~ \.py$ ]]; then
  exit 0
fi

cd /var/home/olino3/git/LEDMatrix
uv run ruff format --quiet "$file" 2>/dev/null
uv run ruff check --fix --quiet "$file" 2>/dev/null
exit 0
