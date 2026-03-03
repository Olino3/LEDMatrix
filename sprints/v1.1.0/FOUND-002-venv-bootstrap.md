# FOUND-002 — Virtual Environment Bootstrap Everywhere

> **For Claude:** Use `superpowers:writing-plans` before touching any files.

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Chore
**Depends on:** [FOUND-001](FOUND-001-pyproject-uv-migration.md) — `pyproject.toml` and `uv.lock` must exist first
**Blocks:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)

---

## Context

The project `.venv/` directory exists at `/root/LEDMatrix/.venv/` and is already used by the `matrix` CLI (`scripts/matrix_cli.py` auto-detects `.venv/bin/python3`). However:

1. **Systemd services** call `/usr/bin/python3` (system Python), not the venv. This means runtime dependencies must be system-wide or the service breaks silently.
2. **`scripts/install/install_service.sh`** hard-codes `/usr/bin/python3` in the generated unit files.
3. There is no automated venv creation step — if the venv is missing, nothing creates it.

This ticket ensures that:
- All places that launch Python use `<project_root>/.venv/bin/python3`
- The venv is created automatically when missing (via both the `matrix` CLI and the install script)

---

## Acceptance Criteria

- [ ] `systemd/ledmatrix.service` template uses `__VENV_PYTHON__` placeholder instead of `/usr/bin/python3`
- [ ] `systemd/ledmatrix-web.service` template uses `__VENV_PYTHON__` placeholder
- [ ] `scripts/install/install_service.sh` resolves `VENV_PYTHON` to `<project_root>/.venv/bin/python3` and substitutes it when generating both unit files
- [ ] `scripts/install/install_service.sh` creates the venv via `uv sync` if `.venv/` does not exist before installing services
- [ ] `scripts/matrix_cli.py` checks for `.venv/` at startup; if absent, runs `uv sync` automatically before proceeding (or exits with a clear message if `uv` itself is not installed)
- [ ] Running `matrix run` from a freshly cloned repo (no `.venv/`) either auto-creates the venv or prints actionable instructions
- [ ] No change to public APIs or plugin behavior

---

## Implementation Checklist

### 1. Update systemd service templates

**File:** `systemd/ledmatrix.service`

- [ ] Replace `ExecStart=/usr/bin/python3` with `ExecStart=__VENV_PYTHON__`
- [ ] The substitution happens in the install script, not at runtime

**File:** `systemd/ledmatrix-web.service`

- [ ] Replace `ExecStart=/usr/bin/python3` with `ExecStart=__VENV_PYTHON__`
- [ ] Confirm `WorkingDirectory=__PROJECT_ROOT_DIR__` is still present (it is)

After change, `ledmatrix.service` should look like:
```ini
ExecStart=__VENV_PYTHON__ __PROJECT_ROOT_DIR__/run.py
```

### 2. Update `scripts/install/install_service.sh`

- [ ] After resolving `PROJECT_ROOT_DIR`, also define:
  ```bash
  VENV_PYTHON="${PROJECT_ROOT_DIR}/.venv/bin/python3"
  ```
- [ ] Add a venv bootstrap block before the systemd install logic:
  ```bash
  if [ ! -x "$VENV_PYTHON" ]; then
      echo "No .venv found — bootstrapping with uv..."
      if ! command -v uv >/dev/null 2>&1; then
          echo "ERROR: 'uv' is not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
          exit 1
      fi
      uv sync --project "$PROJECT_ROOT_DIR"
  fi
  ```
- [ ] In the `sed` substitution line that generates the unit file, add `s|__VENV_PYTHON__|$VENV_PYTHON|g`
- [ ] Verify the dynamically-generated `ledmatrix-web.service` block (the heredoc starting at line 51) also substitutes correctly — update it to use `$VENV_PYTHON` instead of `/usr/bin/python3`

### 3. Update `scripts/matrix_cli.py` — venv guard

**File:** `scripts/matrix_cli.py` — the block around line 33:

```python
_venv_python = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"
PYTHON = str(_venv_python) if _venv_python.exists() else sys.executable
```

- [ ] Replace this passive fallback with an active check:

```python
_venv_python = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"

if not _venv_python.exists():
    # Attempt to bootstrap automatically
    uv = shutil.which("uv")
    if uv:
        console.print("[yellow]No .venv found — running uv sync to bootstrap...[/yellow]")
        result = subprocess.run([uv, "sync", "--project", str(LEDMATRIX_ROOT)], check=False)
        if result.returncode != 0:
            console.print("[red]uv sync failed. Run manually: uv sync[/red]")
            sys.exit(1)
    else:
        console.print(
            "[red]No .venv found and 'uv' is not installed.[/red]\n"
            "Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            "Then run:    uv sync"
        )
        sys.exit(1)

PYTHON = str(_venv_python)
```

- [ ] This guard runs once at import time, before any Click command executes
- [ ] Guard is skipped if `.venv/bin/python3` already exists (the common case; no performance hit)

### 4. Update `scripts/dev/run_emulator.sh`

- [ ] Read `scripts/dev/run_emulator.sh`
- [ ] If it calls `python3` directly, update it to call `../../.venv/bin/python3` (or detect the venv root)

### 5. Smoke test locally

- [ ] Temporarily rename `.venv/` to `.venv_bak/`, run `matrix run` — verify it auto-creates the venv
- [ ] Restore `.venv_bak/` → `.venv/`
- [ ] Confirm `systemd/ledmatrix.service` no longer contains `/usr/bin/python3`

### 6. Commit

```bash
git add systemd/ledmatrix.service systemd/ledmatrix-web.service \
        scripts/install/install_service.sh scripts/matrix_cli.py \
        scripts/dev/run_emulator.sh
git commit -m "chore(infra): use venv python in systemd services and auto-bootstrap venv"
```

---

## Verification Steps

```bash
# 1. Service templates no longer hard-code system python
grep -n "/usr/bin/python3" systemd/ledmatrix.service && echo "FAIL" || echo "OK: no /usr/bin/python3 in ledmatrix.service"
grep -n "/usr/bin/python3" systemd/ledmatrix-web.service && echo "FAIL" || echo "OK: no /usr/bin/python3 in ledmatrix-web.service"

# 2. Templates contain the venv placeholder
grep "__VENV_PYTHON__" systemd/ledmatrix.service && echo "OK: placeholder present"

# 3. Install script references VENV_PYTHON
grep "VENV_PYTHON" scripts/install/install_service.sh && echo "OK: venv logic in install script"

# 4. matrix CLI contains venv bootstrap logic
grep "uv sync" scripts/matrix_cli.py && echo "OK: venv auto-bootstrap in CLI"

# 5. Python resolves to venv in CLI
python3 -c "
import sys, pathlib
sys.argv = ['matrix']
# Just confirm PYTHON variable resolves to venv path
root = pathlib.Path('.').resolve()
venv_py = root / '.venv' / 'bin' / 'python3'
assert venv_py.exists(), f'venv python not found at {venv_py}'
print('OK: venv python exists at', venv_py)
"
```

---

## Notes

- The `ExecStart` line in the _dynamically generated_ web service content (the heredoc in `install_service.sh` lines 51–70) must also be updated — it is separate from the template file.
- On Raspberry Pi, `root` runs the display service; confirm `root` owns the `.venv/` or that permissions allow execution.
- Do not remove `/usr/bin/python3` fallback in scripts that run _before_ the venv is created (e.g., the `uv` bootstrap step itself must use system Python or the `uv` binary directly).
