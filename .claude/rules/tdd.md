# TDD Enforcement

All changes to this codebase follow strict RED/GREEN test-driven development.

## The Workflow

1. **RED:** Write a failing test that specifies the desired behavior. Commit it.
2. **GREEN:** Implement the minimum code to make the test pass. Commit it.
3. **REFACTOR:** Clean up if needed. Tests must still pass.

## Rules

- For ANY change to ANY source file: write a failing test first (RED), commit it, then implement (GREEN).
- If you touch existing code that lacks tests, add tests for the touched behavior before changing it (Boy Scout Rule).
- Never mark a feature complete without running `pytest` and confirming tests pass.
- Never write production code to make a test compile — a test that errors on import is wrong.
- Test file location mirrors source: `test/test_<module>.py` for `src/<module>.py`.

## Agents

- `@red-agent <spec>` — generates failing tests for a feature spec or class description
- `@green-agent` — implements minimum code to make the failing RED tests pass

## Running Tests

```bash
# Standard test run (use this — 7 pre-existing failures are expected)
EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins

# Specific file
EMULATOR=true .venv/bin/pytest test/test_<module>.py -v
```
