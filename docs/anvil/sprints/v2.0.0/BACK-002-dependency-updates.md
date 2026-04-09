# BACK-002 — Update Dependencies for FastAPI Stack

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Chore
**Depends on:** [BACK-001](BACK-001-fastapi-app-scaffold.md)
**Blocks:** [BACK-004](BACK-004-middleware-stack.md), [BACK-005](BACK-005-api-routes-system.md)

---

## Context

The current `pyproject.toml` lists Flask, flask-wtf, and flask-limiter as core dependencies. Phase 2 replaces these with FastAPI, uvicorn, pydantic-settings, sse-starlette, and python-multipart. The Flask dependencies remain until BACK-008 (cleanup) to avoid breaking the existing web interface during the transition, but all new code must import from the FastAPI stack.

---

## Acceptance Criteria

- [ ] `pyproject.toml` adds: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sse-starlette`, `python-multipart`, `httpx` (for test client)
- [ ] `httpx` is added under `[project.optional-dependencies.test]` (FastAPI test client)
- [ ] `uv lock` regenerates `uv.lock` without conflicts
- [ ] `uv sync --extra test --extra dev --extra emulator` installs all new deps successfully
- [ ] Flask deps are NOT removed yet (coexistence during transition)
- [ ] Version constraints are set with minimum versions and upper bounds

---

## Implementation Checklist

### 1. Add new dependencies to `pyproject.toml`

- [ ] Add to `[project.dependencies]`:
  ```
  "fastapi>=0.115.0,<1.0.0",
  "uvicorn[standard]>=0.30.0,<1.0.0",
  "pydantic-settings>=2.2.0,<3.0.0",
  "sse-starlette>=2.0.0,<3.0.0",
  "python-multipart>=0.0.9",
  ```
- [ ] Add to `[project.optional-dependencies.test]`:
  ```
  "httpx>=0.27.0,<1.0.0",
  ```

### 2. Regenerate lock file

- [ ] Run `uv lock` to regenerate `uv.lock`
- [ ] Verify no dependency conflicts

### 3. Smoke test

- [ ] `uv sync --extra test --extra dev --extra emulator` completes without errors
- [ ] `python3 -c "import fastapi; import uvicorn; import pydantic_settings; print('OK')"` succeeds in the venv

### 4. Commit

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add FastAPI, uvicorn, pydantic-settings, sse-starlette dependencies"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. New deps are listed in pyproject.toml
grep -q "fastapi" pyproject.toml && echo "OK: fastapi in pyproject.toml"
grep -q "uvicorn" pyproject.toml && echo "OK: uvicorn in pyproject.toml"
grep -q "pydantic-settings" pyproject.toml && echo "OK: pydantic-settings in pyproject.toml"
grep -q "sse-starlette" pyproject.toml && echo "OK: sse-starlette in pyproject.toml"

# 2. Lock file is regenerated
test -f uv.lock && echo "OK: uv.lock exists"

# 3. Imports work (run inside distrobox)
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && .venv/bin/python3 -c "import fastapi; import uvicorn; import pydantic_settings; import sse_starlette; print(\"OK: all imports\")"'

# 4. Flask deps still present (coexistence)
grep -q "Flask" pyproject.toml && echo "OK: Flask still present"
```

---

## Notes

- `uvicorn[standard]` includes `httptools`, `uvloop`, and `watchfiles` for production performance.
- `python-multipart` is required by FastAPI for form data parsing (file uploads, plugin config forms).
- `httpx` is the recommended test client for FastAPI (replaces Flask's `app.test_client()`).
- Flask dependencies will be removed in BACK-008 after all routes are migrated and verified.
- Pydantic v2 is already a transitive dependency of FastAPI -- no separate pin needed.
