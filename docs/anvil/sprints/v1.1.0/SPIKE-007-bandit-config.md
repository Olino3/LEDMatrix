# SPIKE-007 — Create or Remove `bandit.yaml` Configuration

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Chore / Infrastructure
**Depends on:** [FOUND-005](FOUND-005-precommit-ruff.md)
**Blocks:** _(none)_

---

## Context

The pre-commit config for bandit previously referenced a `bandit.yaml` config file (`-c bandit.yaml`), but this file did not exist in the repository. During FOUND-005, the `-c bandit.yaml` argument was removed so the hook runs with bandit's defaults.

This ticket tracks deciding whether to:
1. Create a `bandit.yaml` with project-specific configuration (skip rules, exclude paths), or
2. Keep using bandit defaults (current state after FOUND-005)

## Decision

**Create `bandit.yaml`** — Running bandit with defaults produces 30 medium/high findings that are all false positives for this project context (single-user Raspberry Pi embedded device). A config file is needed to suppress these and make the pre-commit hook pass cleanly.

## Changes Made

1. Created `bandit.yaml` at repo root with skips for false-positive rules:
   - **B103** (permissive chmod): 0o660/0o755 are intentional for cache files and scripts
   - **B104** (bind 0.0.0.0): Intentional — the web UI must be LAN-accessible
   - **B108** (hardcoded /tmp): Acceptable on a single-user embedded device
   - **B201** (Flask debug=True): Only appears inside `if __name__ == '__main__'` guards
   - **B324** (MD5 hashlib): Used for non-security purposes (config change detection, filename hashing)
2. Re-added `-c bandit.yaml` argument to `.pre-commit-config.yaml`
3. Added inline `# nosec B310` to `src/font_manager.py:269` for a single `urlretrieve` call (URL comes from user config, not untrusted input)

## Acceptance Criteria

- [x] Decision documented on whether a `bandit.yaml` is needed
- [x] Config file created and `-c` argument re-added to `.pre-commit-config.yaml`
- [x] `uv run pre-commit run bandit --all-files` passes
