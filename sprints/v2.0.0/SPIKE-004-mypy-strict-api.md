# SPIKE-004 — Enforce Strict Typing for `src/api/`

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Chore
**Depends on:** [BACK-006](BACK-006-api-routes-plugins.md)
**Blocks:** _(none)_

---

## Context

The ROADMAP specifies that `mypy disallow_untyped_defs = True` should be enforced for `src/api/`. This ticket adds the mypy override configuration and fixes any type errors in the new FastAPI code.

---

## Acceptance Criteria

- [ ] `pyproject.toml` `[tool.mypy]` has an override for `src/api/` with `disallow_untyped_defs = true`
- [ ] `mypy src/api/` passes with zero errors
- [ ] All route handlers have fully typed parameters and return types
- [ ] All Pydantic models have typed fields
- [ ] No `# type: ignore` comments in `src/api/`

---

## Implementation Checklist

### 1. Add mypy override

- [ ] Add to `pyproject.toml`:
  ```toml
  [[tool.mypy.overrides]]
  module = "src.api.*"
  disallow_untyped_defs = true
  ```

### 2. Fix type errors

- [ ] Run `mypy src/api/` and fix all errors
- [ ] Add type annotations to any untyped functions
- [ ] Add `py.typed` marker file to `src/api/`

### 3. Verify

- [ ] `mypy src/api/` returns 0 errors

### 4. Commit

```bash
git add pyproject.toml src/api/
git commit -m "chore(types): enforce strict typing for src/api/ with mypy"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. mypy override exists
grep -A2 "src.api" pyproject.toml | grep -q "disallow_untyped_defs" && echo "OK: mypy override"

# 2. mypy passes
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && .venv/bin/mypy src/api/ --ignore-missing-imports'

# 3. No type: ignore in src/api/
! grep -r "type: ignore" src/api/ --include="*.py" && echo "OK: no type ignores"
```

---

## Notes

- This only applies to `src/api/`. The rest of `src/` keeps the existing lenient mypy config until Phase 8.
- FastAPI and Pydantic have excellent type stub support -- most type errors should be straightforward to fix.
- If third-party libraries lack type stubs, add them to `[tool.mypy.overrides]` with `ignore_missing_imports = true` for those specific modules only.
