# DOCK-002 — .dockerignore File

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Chore
**Depends on:** _(none)_
**Blocks:** _(none)_

---

## Context

A `.dockerignore` file prevents unnecessary files from being included in the Docker build context. Without it, the build context would include `.git/` (~100MB+), `node_modules/`, `.venv/`, test files, and other artifacts that bloat the image and slow builds.

This ticket is independent of the Dockerfile itself and can be done in parallel.

---

## Acceptance Criteria

- [ ] `.dockerignore` exists at the repository root
- [ ] `.git/` directory is excluded
- [ ] `.venv/` directory is excluded
- [ ] `node_modules/` directories are excluded
- [ ] Test files (`test/`) are excluded
- [ ] Build artifacts (`frontend/dist/`, `*.pyc`, `__pycache__/`) are excluded
- [ ] Config secrets (`config/config.json`, `config/config_secrets.json`) are excluded
- [ ] Documentation and sprint planning files are excluded

---

## Implementation Checklist

### 1. Create `.dockerignore`

- [ ] Create `.dockerignore` at the repo root with the following exclusions:
  - Version control: `.git/`, `.gitignore`
  - Python: `.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`
  - Node: `node_modules/`, `frontend/dist/`, `frontend/.angular/`
  - IDE: `.vscode/`, `.idea/`
  - User config (mounted at runtime): `config/config.json`, `config/config_secrets.json`
  - Tests: `test/`
  - Docs/planning: `docs/`, `sprints/`, `*.md` (except `README.md`)
  - CI/tooling: `.github/`, `.claude/`
  - Development: `plugin-repos/`, `*.log`

### 2. Commit

```bash
git add .dockerignore
git commit -m "chore(docker): add .dockerignore to exclude build artifacts and secrets"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. File exists
test -f .dockerignore && echo "OK: .dockerignore exists"

# 2. Key exclusions present
grep -q ".git" .dockerignore && echo "OK: .git excluded"
grep -q ".venv" .dockerignore && echo "OK: .venv excluded"
grep -q "node_modules" .dockerignore && echo "OK: node_modules excluded"
grep -q "config/config.json" .dockerignore && echo "OK: config.json excluded"
grep -q "test/" .dockerignore && echo "OK: test/ excluded"
```

---

## Notes

- The `frontend/dist/` exclusion is intentional -- the Angular SPA is built inside the Docker build (stage 1), not copied from the host.
- `config/config.template.json` should NOT be excluded -- it is needed to generate default config inside the container.
- `plugins/` should NOT be excluded -- plugin source code needs to be in the image for built-in plugins.
- Keep this file in sync with `.gitignore` patterns where they overlap.
