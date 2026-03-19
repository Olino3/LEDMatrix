#!/usr/bin/env bash
# PostToolUse hook: check for architecture violations in src/ Python files
# Called by Claude Code after Edit/Write on .py files in src/

file="$TOOL_INPUT_file_path"

# Only check Python files under src/
if [[ ! "$file" =~ /src/.*\.py$ ]]; then
  exit 0
fi

violations=""

if grep -n 'logging\.getLogger' "$file" 2>/dev/null; then
  violations+="VIOLATION: Use get_logger() from src.logging_config — not logging.getLogger()\n"
fi

if grep -n '\.matrix\.\(width\|height\)' "$file" 2>/dev/null; then
  violations+="VIOLATION: Use display_manager.width/height — not .matrix.width/height\n"
fi

if [[ -n "$violations" ]]; then
  printf "%b" "$violations"
  exit 1
fi
