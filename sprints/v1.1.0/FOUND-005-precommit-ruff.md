# FOUND-005 — Migrate Pre-commit Hooks to `ruff`

> **For Claude:** This is a configuration-only change. No application code changes. Read existing `.pre-commit-config.yaml` before editing.

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Chore
**Depends on:** [FOUND-004](FOUND-004-ci-pipeline.md) — `ruff` config must be in `pyproject.toml` first; CI workflow validates that hooks match CI behavior
**Blocks:** _(none)_

---

## Context

The current `.pre-commit-config.yaml` uses `flake8` (version 7.0.0) for linting and has no formatter. The ROADMAP replaces `flake8` + `isort` (not yet present) with `ruff`, which handles both linting and import sorting in a single, fast tool. The CI pipeline (FOUND-004) uses `ruff` — the pre-commit hooks must mirror CI checks so developers catch issues before pushing.

**Current state of `.pre-commit-config.yaml`:**
- `pre-commit-hooks` v4.5.0 — trailing whitespace, EOF, YAML/JSON check, large files, merge conflict check ✓ keep
- `flake8` 7.0.0 with `--select=E9,F63,F7,F82,B` ✗ replace with ruff
- Local hooks: `no-bare-except`, `no-hardcoded-paths` — evaluate keeping or merging into ruff rules
- `mypy` v1.8.0 — update pin to match `pyproject.toml` version
- `bandit` v1.8.3 — keep as-is
- `gitleaks` v8.24.3 — keep as-is

---

## Acceptance Criteria

- [ ] `flake8` hook is removed from `.pre-commit-config.yaml`
- [ ] `ruff check` hook is added (using the official `astral-sh/ruff-pre-commit` repo)
- [ ] `ruff format` hook is added
- [ ] `ruff` hooks read config from `pyproject.toml` `[tool.ruff]` (no duplicate config in `.pre-commit-config.yaml`)
- [ ] `mypy` hook is updated to match the version in `pyproject.toml` (`[dev]` extra)
- [ ] `pre-commit run --all-files` passes on the current codebase (or only fails on pre-existing issues that are documented)
- [ ] All kept hooks (`pre-commit-hooks`, `bandit`, `gitleaks`, local hooks) still function

---

## Implementation Checklist

### 1. Read current config

- [ ] Read `.pre-commit-config.yaml` in full before making any changes

### 2. Evaluate local hooks

The two local hooks in `.pre-commit-config.yaml`:

- `no-bare-except` — runs `grep -rn "except:\s*pass" src/`. This is valid but `ruff` rule `E722` (bare `except:`) and `SIM105` cover this more precisely. Options:
  - Keep the local hook (simple, explicit), OR
  - Remove it and add `"B"` (flake8-bugbear) + `"SIM"` (flake8-simplify) to `[tool.ruff.lint] select` in `pyproject.toml`
  - **Recommendation:** Remove and rely on ruff `B001` / `E722`

- `no-hardcoded-paths` — runs `grep -rn "/home/chuck/" src/`. This is project-specific and has no ruff equivalent. **Keep it.**

### 3. Update `.pre-commit-config.yaml`

Replace the `flake8` block and `no-bare-except` local hook with ruff hooks:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  # Replaces flake8
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10           # pin to latest stable at implementation time
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: no-hardcoded-paths
        name: Check for hardcoded user paths
        entry: bash -c 'if grep -rn "/home/chuck/" src/; then echo "Found hardcoded user paths"; exit 1; fi'
        language: system
        types: [python]
        pass_filenames: false

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0           # update to match pyproject.toml dev extra
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-pytz]
        args: [--ignore-missing-imports, --no-error-summary]
        pass_filenames: false
        files: ^src/

  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args:
          - '-r'
          - '-ll'
          - '-c'
          - 'bandit.yaml'
          - '-x'
          - './tests,./test,./venv,./.venv,./scripts/prove_security.py,./rpi-rgb-led-matrix-master'

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.3
    hooks:
      - id: gitleaks
```

- [ ] Check the latest `astral-sh/ruff-pre-commit` revision at implementation time (it releases frequently)
- [ ] Check the latest `mirrors-mypy` revision that matches the version pinned in `pyproject.toml`

### 4. Install and run hooks

```bash
# Install pre-commit into the git hooks
uv run pre-commit install

# Run all hooks against all files to see current state
uv run pre-commit run --all-files
```

- [ ] If `ruff check` reports errors, decide: fix them (preferred) or add them to `[tool.ruff.lint] ignore` in `pyproject.toml` with a comment
- [ ] If `ruff format` reformats files, stage and commit them separately as `style: apply ruff format to src/`
- [ ] If `mypy` hook fails on pre-existing type errors, that is expected — do not add `# type: ignore` suppressions; document the pre-existing failures in a comment in this ticket

### 5. Commit

```bash
# First commit: any ruff auto-format changes
git add -u src/
git commit -m "style: apply ruff format to src/"

# Second commit: the hook config change
git add .pre-commit-config.yaml pyproject.toml
git commit -m "chore(dev): replace flake8 with ruff in pre-commit hooks; update mypy pin"
```

---

## Verification Steps

```bash
# 1. flake8 is no longer in the config
grep "flake8" .pre-commit-config.yaml && echo "FAIL: flake8 still present" || echo "OK: flake8 removed"

# 2. ruff-pre-commit is present
grep "astral-sh/ruff-pre-commit" .pre-commit-config.yaml && echo "OK: ruff hook present"

# 3. ruff format hook is present
grep "ruff-format" .pre-commit-config.yaml && echo "OK: ruff-format hook present"

# 4. Hooks install cleanly
uv run pre-commit install && echo "OK: pre-commit installed"

# 5. All hooks run without error (or only pre-existing issues)
uv run pre-commit run --all-files; echo "Exit: $?"

# 6. Confirm ruff check passes standalone
uv run ruff check src/ && echo "OK: ruff check"

# 7. Confirm ruff format produces no diffs
uv run ruff format --check src/ && echo "OK: ruff format (no changes needed)"
```

---

## Notes

- `ruff` and `ruff format` are configured entirely via `pyproject.toml` `[tool.ruff]` and `[tool.ruff.format]`. Do not add `args` to the pre-commit hook beyond `--fix` and `--exit-non-zero-on-fix` — the hook will pick up `pyproject.toml` automatically.
- `--fix` in the ruff hook means safe auto-fixes are applied to staged files. This is the expected behavior for a developer workflow; CI uses `--no-fix` implicitly.
- The `bandit.yaml` config file referenced in the bandit hook — confirm it exists at the repo root before pushing. If it doesn't, remove the `-c bandit.yaml` arg from the hook.
- Do not change the `gitleaks` version — it scans for secrets and should only be updated deliberately.
- mypy `mirrors-mypy` pin should match the version in `pyproject.toml` `[dev]` extras to avoid confusing version mismatches between local hook and CI.
