# SPIKE-006 — Clean Up Flask-Coupled Utilities in `src/web_interface/`

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Refactor
**Depends on:** [BACK-008](BACK-008-flask-removal-cleanup.md)
**Blocks:** _(none)_

---

## Context

After BACK-008 removed Flask and all Flask application code, two files in `src/web_interface/` still contain `from flask import` statements:

- `src/web_interface/api_helpers.py` — `from flask import jsonify, request`
- `src/web_interface/error_handler.py` — `from flask import jsonify`

These files are **dead code** — no FastAPI router, test, or other module in `src/` imports them. They were only consumed by the now-deleted `web_interface/blueprints/api_v3.py`.

This ticket decides their fate: delete them, or migrate them to framework-agnostic utilities if any value remains.

---

## Acceptance Criteria

- [x] `src/web_interface/api_helpers.py` — deleted (dead code, no consumers)
- [x] `src/web_interface/error_handler.py` — deleted (dead code, no consumers)
- [x] No `from flask` or `import flask` statements remain anywhere in `src/`
- [x] Also deleted: `errors.py`, `validators.py`, `logging_config.py` (all dead code)
- [x] All tests pass (1285 passed)

---

## Implementation Options

### Option A: Delete (recommended)

Both files are dead code with no consumers. The FastAPI routers have their own error handling via `src/api/middleware/`. Simply delete both files.

```bash
git rm src/web_interface/api_helpers.py src/web_interface/error_handler.py
```

Also evaluate whether `src/web_interface/errors.py` and `src/web_interface/validators.py` are still imported by anything. If not, delete those too.

### Option B: Migrate to FastAPI

If future work (SPIKE-001, SPIKE-002) would benefit from shared response helpers, rewrite using `fastapi.responses.JSONResponse` instead of `flask.jsonify`. This only makes sense if a consumer is identified.

---

## Files to Examine

| File | Flask imports | Consumers after BACK-008 |
|------|--------------|-------------------------|
| `src/web_interface/api_helpers.py` | `jsonify`, `request` | None |
| `src/web_interface/error_handler.py` | `jsonify` | `api_helpers.py` only |
| `src/web_interface/errors.py` | None (framework-agnostic) | `error_handler.py` only |
| `src/web_interface/validators.py` | Check | Check |

---

## Verification

```bash
# No Flask imports in src/
! grep -r "from flask\|import flask" src/ --include="*.py" && echo "OK: no Flask imports in src/"

# Tests pass
EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins
```
