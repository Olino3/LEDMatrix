# SPIKE-006 — Fix Pre-existing Ruff Lint Violations in `src/`

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Chore / Code Quality
**Depends on:** [FOUND-005](FOUND-005-precommit-ruff.md) — ruff must be the active linter
**Blocks:** _(none)_

---

## Context

During FOUND-005 (migrating pre-commit hooks to ruff), 46 pre-existing lint violations were discovered in `src/`. These were temporarily added to the `[tool.ruff.lint] ignore` list in `pyproject.toml` so that CI and pre-commit hooks pass. This ticket tracks removing those ignores and fixing the underlying code issues.

## Violations to Address

| Rule | Count | Description |
|------|-------|-------------|
| F841 | 17 | Local variable assigned but never used |
| B023 | 12 | Function definition does not bind loop variable |
| B007 | 3 | Loop control variable not used within loop body |
| E722 | 4 | Bare `except:` — should catch specific exceptions |
| F821 | 4 | Undefined name (potential bugs) |
| F401 | 2 | Unused import |
| B905 | 2 | `zip()` without explicit `strict=` parameter |
| E402 | 1 | Module-level import not at top of file |
| B027 | 1 | Empty method in abstract base class without `@abstractmethod` |

**Priority:** F821 (undefined names) should be investigated first — these may be actual bugs.

## Acceptance Criteria

- [ ] All rules in the `# Pre-existing issues` ignore block in `pyproject.toml` are removed
- [ ] `uv run ruff check src/` passes with no violations
- [ ] No behavior regressions introduced by fixes

## Implementation Notes

- F841 / B007: Remove unused variable assignments or prefix with `_`
- B023: Capture loop variables in closure default arguments
- E722: Replace bare `except:` with specific exception types
- F821: Investigate — these may be real bugs or missing imports
- F401: Remove unused imports
- B905: Add `strict=False` to `zip()` calls where lengths may differ
- E402: Restructure imports or add `# noqa: E402` with justification
- B027: Add `@abstractmethod` decorator or add a docstring explaining the hook pattern
