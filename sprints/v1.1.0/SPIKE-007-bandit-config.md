# SPIKE-007 — Create or Remove `bandit.yaml` Configuration

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Chore / Infrastructure
**Depends on:** [FOUND-005](FOUND-005-precommit-ruff.md)
**Blocks:** _(none)_

---

## Context

The pre-commit config for bandit previously referenced a `bandit.yaml` config file (`-c bandit.yaml`), but this file does not exist in the repository. During FOUND-005, the `-c bandit.yaml` argument was removed so the hook runs with bandit's defaults.

This ticket tracks deciding whether to:
1. Create a `bandit.yaml` with project-specific configuration (skip rules, exclude paths), or
2. Keep using bandit defaults (current state after FOUND-005)

## Acceptance Criteria

- [ ] Decision documented on whether a `bandit.yaml` is needed
- [ ] If needed, create the config file and re-add the `-c` argument to `.pre-commit-config.yaml`
- [ ] Verify `uv run pre-commit run bandit --all-files` passes
