# SPIKE-005 — Update CI Pipeline for FastAPI

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Chore
**Depends on:** [BACK-008](BACK-008-flask-removal-cleanup.md)
**Blocks:** _(none)_

---

## Context

The GitHub Actions CI pipeline (set up in Phase 1) needs to be updated for the FastAPI migration. The test workflow needs `httpx` in its dependency set, the typecheck workflow should verify `src/api/` passes strict mypy, and the lint workflow should include the new `src/api/` directory.

---

## Acceptance Criteria

- [ ] `.github/workflows/tests.yml` installs `httpx` (via `--extra test`)
- [ ] `.github/workflows/typecheck.yml` runs strict mypy on `src/api/`
- [ ] All workflows pass after the Flask-to-FastAPI migration
- [ ] Coverage threshold remains at 30% (or increases if new tests raise it)
- [ ] Lint and format checks cover `src/api/`

---

## Implementation Checklist

### 1. Update test workflow

- [ ] Verify `--extra test` in the install step pulls `httpx` (should be automatic from BACK-002)
- [ ] Ensure test command includes `test/test_api_*.py` files

### 2. Update typecheck workflow

- [ ] Add a separate mypy step for `src/api/` with `--disallow-untyped-defs`
- [ ] Keep the existing `mypy src/` step for backward compatibility

### 3. Verify lint coverage

- [ ] Ensure `ruff check src/` covers `src/api/`
- [ ] Ensure `ruff format --check src/` covers `src/api/`

### 4. Test locally

- [ ] Run each workflow command locally to verify before pushing

### 5. Commit

```bash
git add .github/workflows/
git commit -m "ci: update workflows for FastAPI migration"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Workflows are valid YAML
python3 -c "
import yaml, pathlib
for f in pathlib.Path('.github/workflows').glob('*.yml'):
    yaml.safe_load(f.read_text())
    print(f'OK: {f.name}')
"

# 2. Test dependencies include httpx
grep -q "httpx" pyproject.toml && echo "OK: httpx in deps"

# 3. Lint covers src/api/
test -d src/api && echo "OK: src/api/ exists for lint"
```

---

## Notes

- This is a small ticket -- mostly verification that existing CI pipelines work with the new code structure.
- If any CI workflow fails on pre-existing issues unrelated to the migration, document them but do not fix them in this ticket.
