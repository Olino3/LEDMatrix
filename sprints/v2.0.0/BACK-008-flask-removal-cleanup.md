# BACK-008 — Flask Removal and Cleanup

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Refactor
**Depends on:** [BACK-005](BACK-005-api-routes-system.md), [BACK-006](BACK-006-api-routes-plugins.md), [BACK-007](BACK-007-sse-migration.md)
**Blocks:** [SPIKE-001](SPIKE-001-web-interface-v2-shim.md), [SPIKE-002](SPIKE-002-pages-v3-transition.md), [SPIKE-005](SPIKE-005-update-ci-for-fastapi.md)

---

## Context

After all API routes, SSE streams, and middleware are migrated to FastAPI (BACK-005 through BACK-007), the Flask application code is no longer needed. This ticket removes Flask from the dependency tree, deletes the Flask-specific code, and updates all entry points to use the new FastAPI app.

The `web_interface/` directory is NOT fully deleted -- static files, templates, and `cache.py` are retained for the Phase 3 transition. Only Flask-specific code is removed.

---

## Acceptance Criteria

- [x] Flask, flask-wtf, and flask-limiter removed from `pyproject.toml` dependencies
- [x] `uv lock` regenerated without Flask in the dependency tree
- [x] `web_interface/app.py` deleted (all functionality moved to `src/api/`)
- [x] `web_interface/blueprints/api_v3.py` deleted
- [x] `web_interface/blueprints/pages_v3.py` deleted (replaced by SPIKE-002 transition)
- [x] `web_interface/start.py` deleted (replaced by `src/api/start.py`)
- [x] `matrix web` CLI command updated to start uvicorn instead of Flask
- [x] Systemd service file `ledmatrix-web.service` updated for uvicorn
- [x] Flask-based tests deleted (FastAPI equivalents already exist as `test/test_api_*.py`)
- [x] No import of `flask` remains in `web_interface/` or `scripts/`
- [ ] Two files in `src/web_interface/` still have Flask imports (dead code) — tracked in [SPIKE-006](SPIKE-006-cleanup-src-web-interface-flask-utils.md)

---

## Implementation Checklist

### 1. Remove Flask dependencies

- [ ] Remove `Flask>=3.0.0,<4.0.0` from `[project.dependencies]`
- [ ] Remove `flask-wtf>=1.2.0` from `[project.dependencies]`
- [ ] Remove `flask-limiter>=3.5.0` from `[project.dependencies]`
- [ ] Run `uv lock` to regenerate lock file

### 2. Delete Flask application code

- [ ] Delete `web_interface/app.py`
- [ ] Delete `web_interface/blueprints/api_v3.py`
- [ ] Delete `web_interface/blueprints/pages_v3.py`
- [ ] Delete `web_interface/blueprints/__init__.py`
- [ ] Keep `web_interface/static/` (needed until Phase 3)
- [ ] Keep `web_interface/templates/` (needed until Phase 3)
- [ ] Keep `web_interface/cache.py` (if still used; otherwise delete)
- [ ] Keep `web_interface/logging_config.py` (if still used; otherwise move to `src/api/`)

### 3. Update entry points

- [ ] Update `web_interface/start.py` to import and run `src.api.main:app` via uvicorn
- [ ] Update `matrix web` command in `scripts/matrix_cli.py` to start uvicorn
- [ ] Update `systemd/ledmatrix-web.service` ExecStart line for uvicorn

### 4. Update tests

- [ ] Replace `from flask.testing import FlaskClient` with `httpx.AsyncClient`
- [ ] Update `test/test_web_api.py` to use FastAPI test client
- [ ] Update `test/test_web_form_parsing.py` or delete if form parsing is handled by Pydantic
- [ ] Verify all tests pass

### 5. Verify no Flask imports remain

- [ ] `grep -r "from flask" src/ web_interface/` returns empty
- [ ] `grep -r "import flask" src/ web_interface/` returns empty

### 6. Commit

```bash
git rm web_interface/app.py web_interface/blueprints/api_v3.py web_interface/blueprints/pages_v3.py
git add pyproject.toml uv.lock web_interface/start.py scripts/matrix_cli.py
git commit -m "refactor(api): remove Flask, update entry points to FastAPI/uvicorn"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Flask is gone from dependencies
! grep -q "Flask" pyproject.toml && echo "OK: Flask removed from pyproject.toml"
! grep -q "flask-wtf" pyproject.toml && echo "OK: flask-wtf removed"
! grep -q "flask-limiter" pyproject.toml && echo "OK: flask-limiter removed"

# 2. Flask app code is deleted
test ! -f web_interface/app.py && echo "OK: app.py deleted"
test ! -f web_interface/blueprints/api_v3.py && echo "OK: api_v3.py deleted"
test ! -f web_interface/blueprints/pages_v3.py && echo "OK: pages_v3.py deleted"

# 3. No Flask imports remain
! grep -r "from flask" src/ web_interface/ --include="*.py" && echo "OK: no flask imports in src/"
! grep -r "import flask" src/ web_interface/ --include="*.py" && echo "OK: no flask imports"

# 4. Static files and templates still exist (needed for Phase 3)
test -d web_interface/static && echo "OK: static dir preserved"
test -d web_interface/templates && echo "OK: templates dir preserved"

# 5. FastAPI app starts
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && timeout 5 .venv/bin/python3 -c "from src.api.main import app; print(\"OK: FastAPI app loads\")"'

# 6. Tests pass
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/ -q --override-ini=\"addopts=\" --ignore=test/plugins'
```

---

## Notes

- The `web_interface/` directory is NOT fully removed. Static files and templates remain for the HTMX-to-Angular transition in Phase 3. Only Flask-specific Python code is deleted.
- The `web_interface/__init__.py` should remain if `web_interface/cache.py` or `web_interface/logging_config.py` are still imported anywhere.
- `src/web_interface/` (under `src/`) contains `api_helpers.py`, `errors.py`, `validators.py`, `error_handler.py`, and `logging_config.py`. These may need to be migrated to `src/api/` or kept as shared utilities. Evaluate during implementation.
- The `matrix web` CLI command currently runs `app.run()` directly. It should be updated to call `uvicorn.run("src.api.main:app", ...)`.
- Plugin Impact: None directly. The `web_interface_v2` shim is handled in SPIKE-001.
