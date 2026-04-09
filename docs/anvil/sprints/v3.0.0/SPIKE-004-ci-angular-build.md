# SPIKE-004 — CI Pipeline for Angular Build and Tests

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Chore
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md), [SPIKE-001](SPIKE-001-angular-unit-test-setup.md)
**Blocks:** _(none)_

---

## Context

The existing CI pipeline (GitHub Actions) runs Python tests, mypy, and ruff. Phase 3 adds a frontend build that must also be validated in CI. This ticket adds a CI job for Angular build, lint, and test.

---

## Acceptance Criteria

- [ ] GitHub Actions workflow includes an Angular build step
- [ ] `ng build` runs in CI and fails the pipeline if the build fails
- [ ] `ng lint` runs in CI (requires `@angular-eslint` setup)
- [ ] `ng test --watch=false --browsers=ChromeHeadless` runs in CI
- [ ] Frontend CI job uses Node.js 18+ with npm caching
- [ ] CI matrix: Angular job runs in parallel with Python jobs (not sequentially)

---

## Implementation Checklist

### 1. Add Angular lint setup

- [ ] Run `ng add @angular-eslint/schematics` in the Angular project
- [ ] Verify `ng lint` works locally
- [ ] Configure ESLint rules appropriate for the project

### 2. Update GitHub Actions workflow

- [ ] Add a `frontend` job to `.github/workflows/ci.yml` (or create a new workflow)
- [ ] Use `actions/setup-node@v4` with Node.js 18 or 20
- [ ] Cache `node_modules` via `actions/cache` or npm cache
- [ ] Steps: `npm ci` -> `ng lint` -> `ng test --watch=false --browsers=ChromeHeadless` -> `ng build`
- [ ] Job runs in parallel with existing Python CI jobs

### 3. Verify pipeline

- [ ] Push a test branch and confirm the workflow runs successfully
- [ ] Confirm build artifacts are produced (optional: upload as GitHub artifact)

### 4. Commit

```bash
git add .github/workflows/ frontend/
git commit -m "chore(ci): add Angular build, lint, and test to CI pipeline"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Lint works locally
cd frontend && npx ng lint && echo "OK: lint passes"

# 2. CI workflow references frontend
grep -q "frontend" .github/workflows/ci.yml && echo "OK: CI includes frontend"

# 3. Node setup in CI
grep -q "setup-node" .github/workflows/ci.yml && echo "OK: Node setup in CI"
```

---

## Notes

- Chrome headless in CI may require `--no-sandbox` flag. Ensure the CI runner supports it.
- The Angular build output does NOT need to be committed to the repo. It is built fresh in CI and at deploy time.
- Consider caching the Angular build cache (`.angular/cache/`) in CI for faster subsequent builds.
- If the CI workflow file is too large, consider splitting into `ci-python.yml` and `ci-frontend.yml`.
