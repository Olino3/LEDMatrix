# FOUND-001 — Migrate to `pyproject.toml` + `uv`

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Chore
**Depends on:** _(none — start here)_
**Blocks:** [FOUND-002](FOUND-002-venv-bootstrap.md), [FOUND-003](FOUND-003-matrix-cli-install-doctor.md), [FOUND-004](FOUND-004-ci-pipeline.md)

---

## Context

The project currently uses three separate `requirements*.txt` files:

- `requirements.txt` — core runtime + testing + mypy (51 lines)
- `web_interface/requirements.txt` — web-only dependencies, many duplicated from root (58 lines)
- `requirements-emulator.txt` — single entry: `RGBMatrixEmulator`

There is no `pyproject.toml`. Test configuration lives in `pytest.ini`. The project has no standardized way to install just the dependencies needed for a given task (hardware vs. emulator vs. test). This ticket migrates the entire dependency surface to a single `pyproject.toml` with `uv` as the package manager.

**Key constraint:** No `pyproject.toml` exists yet. The `.venv/` directory was created manually. The systemd services currently call `/usr/bin/python3` (system Python). Those are addressed in FOUND-002; this ticket only covers the `pyproject.toml` and `uv.lock`.

---

## Acceptance Criteria

- [ ] A single `pyproject.toml` exists at the repo root
- [ ] All runtime dependencies from `requirements.txt` and `web_interface/requirements.txt` are deduplicated and listed under `[project.dependencies]`
- [ ] Optional dependency groups defined: `[project.optional-dependencies]`
  - `emulator` — `RGBMatrixEmulator`
  - `hardware` — `rpi-rgb-led-matrix` (or equivalent wheel)
  - `dev` — `ruff`, `mypy`, `pre-commit`, `types-requests`, `types-pytz`
  - `test` — `pytest`, `pytest-cov`, `pytest-mock`
- [ ] `uv.lock` is generated and committed
- [ ] `pytest.ini` configuration is migrated to `[tool.pytest.ini_options]` inside `pyproject.toml`
- [ ] `[tool.mypy]` section added to `pyproject.toml` (migrated from any `.mypy.ini` or inline flags)
- [ ] `[tool.ruff]` section added with lint rules and format config (to be used by FOUND-004 and FOUND-005)
- [ ] All three `requirements*.txt` files are deleted
- [ ] `uv sync` (no extras) installs only runtime deps and succeeds in a clean environment
- [ ] `uv sync --extra test --extra dev` installs everything needed for CI
- [ ] `uv sync --extra emulator` works for development without hardware

---

## Implementation Checklist

### 1. Understand the current dependency surface

- [ ] Read `requirements.txt` in full — note every package and its version constraint
- [ ] Read `web_interface/requirements.txt` — identify packages that are identical to root (they should merge), and any that are truly web-only
- [ ] Read `requirements-emulator.txt`
- [ ] Search for any `pip install` calls in scripts: `grep -r "pip install" scripts/` — document what they install so nothing is missed
- [ ] Check `first_time_install.sh` for any additional `pip` calls and note them

### 2. Author `pyproject.toml`

- [ ] Create `pyproject.toml` at repo root with these top-level sections:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ledmatrix"
version = "1.1.0"
description = "LED matrix display controller for Raspberry Pi"
requires-python = ">=3.10"
dependencies = [
    # list merged, deduplicated deps here
]

[project.optional-dependencies]
emulator = ["RGBMatrixEmulator"]
hardware = []          # rpi-rgb-led-matrix is installed from source; leave empty or add wheel if available
dev     = ["ruff>=0.4.0", "mypy>=1.5.0", "pre-commit>=3.7.0", "types-requests", "types-pytz"]
test    = ["pytest>=7.4.0,<9", "pytest-cov>=4.1.0", "pytest-mock>=3.11.0"]
```

- [ ] Add `[tool.pytest.ini_options]` — copy settings from `pytest.ini` verbatim, then delete `pytest.ini`
- [ ] Add `[tool.mypy]` with `ignore_missing_imports = true`, `warn_unused_ignores = true`
- [ ] Add `[tool.ruff]` with a starter config:

```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

### 3. Generate the lock file

- [ ] Install `uv` if not present: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Run `uv lock` from the repo root to generate `uv.lock`
- [ ] Inspect `uv.lock` briefly — confirm it resolves without conflicts on Python 3.10, 3.11, 3.12

### 4. Delete the old files

- [ ] Delete `requirements.txt`
- [ ] Delete `web_interface/requirements.txt`
- [ ] Delete `requirements-emulator.txt`
- [ ] Delete `pytest.ini` (after confirming settings are in `pyproject.toml`)

### 5. Smoke test

- [ ] `uv sync` completes without error
- [ ] `uv run pytest --co -q` (collect-only) exits without import errors
- [ ] `uv run mypy src/ --ignore-missing-imports` exits 0 or only reports pre-existing errors

### 6. Commit

```bash
git add pyproject.toml uv.lock
git rm requirements.txt web_interface/requirements.txt requirements-emulator.txt pytest.ini
git commit -m "chore(deps): migrate to pyproject.toml + uv, remove requirements.txt files"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. uv.lock is committed
git show HEAD:uv.lock | head -5

# 2. Old files are gone
test ! -f requirements.txt && echo "OK: requirements.txt removed"
test ! -f web_interface/requirements.txt && echo "OK: web_interface/requirements.txt removed"
test ! -f requirements-emulator.txt && echo "OK: requirements-emulator.txt removed"
test ! -f pytest.ini && echo "OK: pytest.ini removed"

# 3. pyproject.toml parses correctly (Python-based check)
python3 -c "import tomllib; tomllib.loads(open('pyproject.toml').read()); print('OK: pyproject.toml is valid TOML')"

# 4. All optional groups resolve without error
uv sync --extra test --extra dev && echo "OK: test+dev sync"
uv sync --extra emulator && echo "OK: emulator sync"

# 5. Tests still pass (use existing test env to avoid slow re-install)
EMULATOR=true uv run pytest test/ -q --ignore=test/plugins
```

---

## Notes

- The `hardware` optional group is intentionally empty for now. The `rgbmatrix` C extension is built from source during `first_time_install.sh` and cannot be distributed as a pure wheel. FOUND-003 will handle this when absorbing the install script.
- `web_interface/requirements.txt` has many duplicates of the root file. After merging, verify the web interface starts cleanly: `uv run python3 web_interface/start.py &` (then kill it). The goal is one unified dep list; the web interface is part of the same Python process in production.
- Do NOT yet update `systemd/ledmatrix.service` or `systemd/ledmatrix-web.service` to use the venv — that is FOUND-002's job.
- The `rpi-rgb-led-matrix` library is compiled from C source and is not on PyPI. Leave `hardware` extra empty; document this in a comment in `pyproject.toml`.
