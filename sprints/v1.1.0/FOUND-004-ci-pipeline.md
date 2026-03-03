# FOUND-004 — GitHub Actions CI Pipeline

> **For Claude:** Use `superpowers:writing-plans` before authoring workflow files. No application code changes; only `.github/workflows/` files.

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Chore / Infrastructure
**Depends on:** [FOUND-001](FOUND-001-pyproject-uv-migration.md) — `pyproject.toml` and `uv.lock` must exist so CI can install deps with `uv`
**Blocks:** [FOUND-005](FOUND-005-precommit-ruff.md)

---

## Context

The repo currently has no GitHub Actions workflows — `.github/` contains only `FUNDING.yml`. Every push and PR is unvalidated by automation. This ticket introduces four workflow files that together enforce: code formatting, type safety, test coverage, and dependency security.

All workflows use `uv` for dependency installation (fast, reproducible via `uv.lock`). Tests run across Python 3.10, 3.11, and 3.12 (the versions the ROADMAP targets).

**Note:** The `ruff` lint/format tools must be declared in `pyproject.toml` `[tool.ruff]` (done in FOUND-001) before this ticket can finalize its config. Coordinate with FOUND-001.

---

## Acceptance Criteria

- [ ] `.github/workflows/lint.yml` — runs `ruff check` and `ruff format --check` on every push and PR to `main` and `develop`
- [ ] `.github/workflows/typecheck.yml` — runs `mypy src/` on every PR to `main` and `develop`
- [ ] `.github/workflows/tests.yml` — runs `pytest` with coverage on Python 3.10, 3.11, 3.12; uploads coverage report as artifact; fails if coverage < 30%
- [ ] `.github/workflows/audit.yml` — runs `uv pip audit` to flag known CVEs; runs on every push to `main` and weekly schedule
- [ ] All four workflows use `uv` to install dependencies from `uv.lock`
- [ ] Workflows pass on the current codebase (existing test failures are acceptable as long as coverage ≥ 30%)
- [ ] Workflows are named clearly and appear in the GitHub Actions tab with human-readable job names

---

## Implementation Checklist

### 1. Create `.github/workflows/lint.yml`

```yaml
name: Lint & Format

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  ruff:
    name: ruff check + format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Install dev dependencies
        run: uv sync --extra dev

      - name: Lint (ruff check)
        run: uv run ruff check src/

      - name: Format check (ruff format)
        run: uv run ruff format --check src/
```

- [ ] Create file at `.github/workflows/lint.yml`

### 2. Create `.github/workflows/typecheck.yml`

```yaml
name: Type Check

on:
  pull_request:
    branches: [main, develop]

jobs:
  mypy:
    name: mypy src/
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Install dev + test dependencies
        run: uv sync --extra dev --extra test --extra emulator

      - name: Type check
        run: uv run mypy src/ --ignore-missing-imports
```

- [ ] Create file at `.github/workflows/typecheck.yml`

### 3. Create `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  pytest:
    name: pytest (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --extra test --extra emulator

      - name: Run tests
        env:
          EMULATOR: "true"
        run: |
          uv run pytest test/ \
            --ignore=test/plugins \
            -q \
            --cov=src \
            --cov-report=term-missing \
            --cov-report=xml:coverage.xml \
            --cov-fail-under=30

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        if: matrix.python-version == '3.12'
        with:
          name: coverage-report
          path: coverage.xml
```

- [ ] Create file at `.github/workflows/tests.yml`
- [ ] Note: `--ignore=test/plugins` mirrors the existing local test invocation pattern

### 4. Create `.github/workflows/audit.yml`

```yaml
name: Dependency Audit

on:
  push:
    branches: [main]
  schedule:
    # Every Monday at 08:00 UTC
    - cron: "0 8 * * 1"

jobs:
  audit:
    name: uv pip audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --extra test --extra dev --extra emulator

      - name: Audit dependencies
        run: uv pip audit
```

- [ ] Create file at `.github/workflows/audit.yml`

### 5. Validate locally with `act` (optional but recommended)

If `act` is installed (GitHub Actions local runner):
```bash
act push -W .github/workflows/lint.yml --container-architecture linux/amd64
```

If not, push to a feature branch and observe the Actions tab in GitHub.

### 6. Commit

```bash
git add .github/workflows/
git commit -m "ci: add GitHub Actions workflows for lint, typecheck, tests, and audit"
```

---

## Verification Steps

After pushing to a branch with a PR open against `main` or `develop`:

```bash
# 1. Verify workflow files are syntactically valid YAML
python3 -c "
import yaml, pathlib
for f in pathlib.Path('.github/workflows').glob('*.yml'):
    yaml.safe_load(f.read_text())
    print(f'OK: {f.name}')
"

# 2. Verify ruff is available in the venv (needed for lint workflow)
uv run ruff --version

# 3. Dry-run the test command locally
EMULATOR=true uv run pytest test/ --ignore=test/plugins -q --cov=src --cov-fail-under=30

# 4. Dry-run the type check locally
uv run mypy src/ --ignore-missing-imports

# 5. Dry-run the audit locally
uv pip audit
```

In the GitHub Actions UI:
- [ ] All four workflow files appear in the "Actions" tab
- [ ] `lint` workflow passes on the current code (or fails only on pre-existing ruff violations — document these)
- [ ] `tests` workflow passes on Python 3.10, 3.11, 3.12 with coverage ≥ 30%
- [ ] `audit` workflow passes (no known CVEs in current deps)

---

## Notes

- `astral-sh/setup-uv@v3` is the official GitHub Action for installing `uv`. Check [the releases page](https://github.com/astral-sh/setup-uv/releases) for the latest pinned version at implementation time.
- `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/upload-artifact@v4` are the latest stable versions as of early 2026.
- The `tests` workflow uses `fail-fast: false` so all three Python versions run even if one fails — useful during initial rollout.
- `uv pip audit` requires `pip-audit` to be installed by `uv`. If it errors, run `uv add --dev pip-audit` and regenerate `uv.lock`.
- The coverage threshold is set to 30% to match the existing `pytest.ini` floor. FOUND-008 (Phase 8) will raise it to 70%.
- The `typecheck` workflow only runs on PRs (not push to `main`) to avoid blocking hotfixes; adjust as needed.
