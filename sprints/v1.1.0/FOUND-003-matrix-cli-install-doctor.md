# FOUND-003 — `matrix` CLI: `install`, `setup`, and `doctor` Commands

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for new logic added to the CLI.

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Feature
**Depends on:** [FOUND-001](FOUND-001-pyproject-uv-migration.md), [FOUND-002](FOUND-002-venv-bootstrap.md)
**Blocks:** _(none)_

---

## Context

The current `matrix` CLI (`scripts/matrix_cli.py`) handles dev-time operations: `run`, `web`, `logs`, `service`, and `plugin` subcommands. It does NOT handle installation or system health checks.

Today, first-time setup requires running `first_time_install.sh` — a 700+ line Bash script at the repo root. There are also root-level `start_display.sh` and `stop_display.sh` scripts, plus `web_interface/run.sh`, that duplicate functionality already in the CLI. Users and agents end up confused about which entry point to use.

This ticket:
1. Adds `matrix install` and `matrix setup` that absorb the key logic from `first_time_install.sh`
2. Adds `matrix doctor` for health checking
3. Deprecates (adds clear warning) the legacy shell scripts without deleting them yet (deletion in FOUND-003 follow-up or Phase 2)

**Reference files to read before starting:**
- `scripts/matrix_cli.py` (full file — understand existing command structure, helper functions)
- `first_time_install.sh` (understand what it does — full file is ~700 lines; skim sections via `grep "^# ==\|^echo\|^CURRENT_STEP"`)
- `scripts/install/install_service.sh`
- `systemd/ledmatrix.service`, `systemd/ledmatrix-web.service`

---

## Acceptance Criteria

- [ ] `matrix setup` command exists: creates/syncs the `.venv/` via `uv sync` and reports success
- [ ] `matrix install` command exists: runs `matrix setup` then installs systemd services (calls `install_service.sh`) and optionally builds `rgbmatrix` from source
- [ ] `matrix doctor` command exists and checks:
  - [ ] `.venv/` exists and `python3 -c "import PIL"` succeeds inside it
  - [ ] `uv` is installed and on PATH
  - [ ] `config/config.json` exists (or `config/config.template.json` is present as a fallback guide)
  - [ ] `config/config_secrets.json` exists (warn if missing, not error)
  - [ ] systemd services are installed (`/etc/systemd/system/ledmatrix.service` exists)
  - [ ] systemd services are active (calls `systemctl is-active ledmatrix`)
  - [ ] `plugins/` directory exists and contains at least one plugin
  - [ ] Hardware detection: `/dev/mem` exists (Pi hardware) or `EMULATOR=true` is set
  - [ ] Prints a rich formatted table of pass/warn/fail results; exits non-zero if any check fails
- [ ] `start_display.sh`, `stop_display.sh`, and `web_interface/run.sh` each print a deprecation warning at the top directing users to `matrix run` / `matrix service start` / `matrix web`
- [ ] `matrix --help` lists all commands including the new ones

---

## Implementation Checklist

### 1. Read the existing CLI thoroughly

- [ ] Read `scripts/matrix_cli.py` lines 1–end — map all existing commands and helper functions
- [ ] Read `first_time_install.sh` — identify the logical sections (OS check, apt packages, Python install, rgbmatrix build, pip install, config setup, service install)
- [ ] Note: the full rgbmatrix C-extension build from source is complex and hardware-specific. For this ticket, `matrix install` will delegate to the existing `install_service.sh` for service setup and call `uv sync` for Python deps. The C build remains a documented manual step (or a future ticket).

### 2. Add `matrix setup` command

In `scripts/matrix_cli.py`, add after the existing `web` command:

```python
@cli.command()
@click.option("--extras", multiple=True, default=("emulator",),
              show_default=True, help="uv extras to install (repeatable).")
def setup(extras: tuple) -> None:
    """Create or sync the .venv using uv. Run this after cloning or pulling."""
    uv = shutil.which("uv")
    if not uv:
        console.print("[red]'uv' not found. Install it:[/red]")
        console.print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)

    extras_flags = []
    for extra in extras:
        extras_flags += ["--extra", extra]

    console.print(Rule("[green]setup[/green]"))
    console.print(f"  Syncing deps with extras: {', '.join(extras) or 'none'}")
    rc = _run([uv, "sync", *extras_flags], cwd=str(LEDMATRIX_ROOT))
    if rc == 0:
        console.print("[green]✓ .venv is ready[/green]")
    sys.exit(rc)
```

### 3. Add `matrix install` command

```python
@cli.command()
@click.option("--no-services", is_flag=True, help="Skip systemd service installation.")
@click.option("--emulator", is_flag=True, help="Install emulator extras instead of hardware.")
def install(no_services: bool, emulator: bool) -> None:
    """Full installation: sync deps and optionally install systemd services."""
    console.print(Rule("[green]install[/green]"))

    # Step 1: Setup venv
    extras = ("emulator",) if emulator else ()
    ctx = click.get_current_context()
    ctx.invoke(setup, extras=extras)

    # Step 2: Ensure config.json exists
    config_template = LEDMATRIX_ROOT / "config" / "config.template.json"
    config_file = LEDMATRIX_ROOT / "config" / "config.json"
    if not config_file.exists() and config_template.exists():
        import shutil as _shutil
        _shutil.copy(config_template, config_file)
        console.print("[green]✓ Created config/config.json from template[/green]")
    elif config_file.exists():
        console.print("[dim]config/config.json already exists — skipping[/dim]")
    else:
        console.print("[yellow]⚠ No config template found — create config/config.json manually[/yellow]")

    # Step 3: Install systemd services (requires sudo)
    if no_services:
        console.print("[dim]Skipping service installation (--no-services)[/dim]")
    else:
        install_script = LEDMATRIX_ROOT / "scripts" / "install" / "install_service.sh"
        if not install_script.exists():
            console.print(f"[red]install_service.sh not found at {install_script}[/red]")
            sys.exit(1)
        console.print("  Installing systemd services (may prompt for sudo)...")
        rc = _run(["sudo", "bash", str(install_script)])
        if rc != 0:
            console.print("[red]Service installation failed[/red]")
            sys.exit(rc)
        console.print("[green]✓ Services installed[/green]")

    console.print(Panel("[green]Installation complete![/green]\n\nRun [bold]matrix doctor[/bold] to verify.", border_style="green"))
```

### 4. Add `matrix doctor` command

This is the most involved new command. It runs a series of checks and renders a table.

```python
@cli.command()
def doctor() -> None:
    """Check system health: venv, config, services, hardware."""
    import importlib.util, platform

    console.print(Rule("[green]doctor[/green]"))
    rows: list[tuple[str, str, str]] = []  # (check_name, status_icon, detail)
    any_fail = False

    def ok(name: str, detail: str = "") -> None:
        rows.append((name, "[green]✓ PASS[/green]", detail))

    def warn(name: str, detail: str = "") -> None:
        rows.append((name, "[yellow]⚠ WARN[/yellow]", detail))

    def fail(name: str, detail: str = "") -> None:
        nonlocal any_fail
        any_fail = True
        rows.append((name, "[red]✗ FAIL[/red]", detail))

    # --- uv ---
    uv_path = shutil.which("uv")
    if uv_path:
        ok("uv installed", uv_path)
    else:
        fail("uv installed", "Not found — run: curl -LsSf https://astral.sh/uv/install.sh | sh")

    # --- venv ---
    venv_py = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        result = subprocess.run([str(venv_py), "-c", "import PIL; print(PIL.__version__)"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            ok(".venv / Pillow", f"Pillow {result.stdout.strip()}")
        else:
            fail(".venv / Pillow", "Pillow import failed — run: matrix setup")
    else:
        fail(".venv", f"Not found at {venv_py} — run: matrix setup")

    # --- config.json ---
    cfg = LEDMATRIX_ROOT / "config" / "config.json"
    if cfg.exists():
        ok("config/config.json", str(cfg))
    else:
        fail("config/config.json", "Missing — run: matrix install  (or copy from config.template.json)")

    # --- config_secrets.json ---
    secrets = LEDMATRIX_ROOT / "config" / "config_secrets.json"
    if secrets.exists():
        ok("config/config_secrets.json", str(secrets))
    else:
        warn("config/config_secrets.json", "Missing — plugins needing API keys will error")

    # --- plugins dir ---
    plugins_dir = LEDMATRIX_ROOT / "plugins"
    plugin_count = len(list(plugins_dir.glob("*/manifest.json"))) if plugins_dir.exists() else 0
    if plugin_count > 0:
        ok("plugins/", f"{plugin_count} plugin(s) found")
    elif plugins_dir.exists():
        warn("plugins/", "Directory exists but no plugins installed")
    else:
        fail("plugins/", "plugins/ directory missing")

    # --- systemd services ---
    for unit in ("ledmatrix", "ledmatrix-web"):
        unit_file = pathlib.Path(f"/etc/systemd/system/{unit}.service")
        if not unit_file.exists():
            warn(f"{unit}.service", "Not installed (OK on dev machine, required on Pi)")
            continue
        result = subprocess.run(["systemctl", "is-active", unit],
                                capture_output=True, text=True)
        status = result.stdout.strip()
        if status == "active":
            ok(f"{unit}.service", "active")
        else:
            warn(f"{unit}.service", f"status: {status}")

    # --- hardware / emulator ---
    dev_mem = pathlib.Path("/dev/mem")
    emulator_env = os.environ.get("EMULATOR", "").lower() in ("1", "true", "yes")
    if dev_mem.exists():
        ok("Hardware (/dev/mem)", "Pi hardware detected")
    elif emulator_env:
        ok("Emulator mode", "EMULATOR=true set")
    else:
        warn("Hardware", "/dev/mem not found and EMULATOR not set — set EMULATOR=true for dev")

    # --- Python version ---
    py_ver = platform.python_version()
    major, minor, _ = py_ver.split(".")
    if (int(major), int(minor)) >= (3, 10):
        ok(f"Python {py_ver}", str(venv_py))
    else:
        fail(f"Python {py_ver}", "Requires Python 3.10+")

    # Render table
    table = Table(title="LEDMatrix Health Check", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")
    for name, status, detail in rows:
        table.add_row(name, status, detail)
    console.print(table)

    if any_fail:
        console.print("\n[red]One or more checks failed. Fix the issues above and re-run:[/red]")
        console.print("  [bold]matrix doctor[/bold]")
        sys.exit(1)
    else:
        console.print("\n[green]All checks passed![/green]")
```

- [ ] Add `import pathlib` at the top of the file if not already imported (it is — check line 14)

### 5. Add deprecation warnings to legacy scripts

- [ ] Edit `start_display.sh` — add at the top (after `#!/bin/bash`):
  ```bash
  echo "⚠  DEPRECATED: start_display.sh is deprecated. Use: matrix service start" >&2
  echo "   This script will be removed in a future release." >&2
  ```
- [ ] Edit `stop_display.sh` — same pattern, direct to `matrix service stop`
- [ ] Edit `web_interface/run.sh` — same pattern, direct to `matrix web`
- [ ] Do NOT edit `first_time_install.sh` yet (it's still the canonical full install path until `matrix install` is fully hardened)

### 6. Update `matrix --help` output

- [ ] Run `matrix --help` and verify all three new commands appear in the listing
- [ ] Ensure each new command has a meaningful docstring (shown in help)

### 7. Commit

```bash
git add scripts/matrix_cli.py start_display.sh stop_display.sh web_interface/run.sh
git commit -m "feat(cli): add matrix install, setup, and doctor commands; deprecate legacy scripts"
```

---

## Verification Steps

```bash
# 1. New commands exist and show help
matrix setup --help
matrix install --help
matrix doctor --help

# 2. matrix setup creates/validates the venv
matrix setup && echo "OK: setup succeeded"

# 3. matrix doctor exits 0 in a healthy dev environment
EMULATOR=true matrix doctor; echo "Exit: $?"

# 4. matrix doctor exits non-zero if config is missing (test by temporarily renaming it)
mv config/config.json config/config.json.bak
EMULATOR=true matrix doctor; echo "Expected exit: 1, got: $?"
mv config/config.json.bak config/config.json

# 5. Deprecation warnings appear
bash start_display.sh 2>&1 | grep "DEPRECATED"
bash stop_display.sh 2>&1 | grep "DEPRECATED"
bash web_interface/run.sh 2>&1 | grep "DEPRECATED"

# 6. All existing commands still work
matrix --help
matrix logs --help
matrix service --help
matrix plugin --help
```

---

## Notes

- The `matrix install --no-services` path is useful for CI/dev environments where there is no systemd.
- `matrix doctor` should be readable without a terminal (no spinners that need clearing) — use a plain `Table` so it works in CI logs.
- The rgbmatrix C-extension build (from `rpi-rgb-led-matrix-master/`) is intentionally excluded from `matrix install` in this phase — it requires OS-level `apt` packages and compilation that is risky to automate blindly. Add a `warn()` check in `matrix doctor` if the `rgbmatrix` module cannot be imported and `EMULATOR` is not set.
- Keep `_require_web()` guard for API-dependent plugin commands — do not remove.

### Downstream Notes from FOUND-002

The following changes from FOUND-002 impact this ticket:

1. **Venv bootstrap already exists in `matrix_cli.py`:** The active venv guard (lines 34-50) runs `uv sync --project` automatically if `.venv/` is missing. `matrix setup` can reuse this pattern or delegate to it — no need to reimplement the bootstrap logic.

2. **`install_service.sh` auto-bootstraps venv:** The install script now creates `.venv/` via `uv sync` before installing services. `matrix install` calling this script will get venv creation for free.

3. **`install_web_service.sh` also updated:** This separate script now uses `$VENV_PYTHON` in its generated service file and includes the same bootstrap block. Ensure `matrix install` invokes both scripts or uses the combined `install_service.sh` which handles both services.

4. **`start_web_conditionally.py` simplified:** The `install_dependencies()` / `dependencies_installed()` functions and `DEPS_MARKER` (`.web_deps_installed`) have been removed. `matrix doctor` should **not** check for the `.web_deps_installed` marker file — it no longer exists.

5. **Plugin dependency installation uses system pip:** `scripts/install_plugin_dependencies.sh` and `src/plugin_system/plugin_loader.py` still use `pip install --break-system-packages`. This is tracked in [SPIKE-003](SPIKE-003-plugin-deps-venv-migration.md) and is not blocking for FOUND-003.

6. **`first_time_install.sh` dead code:** Lines 634-729 and 768-778 check for `requirements.txt` / `web_interface/requirements.txt` which no longer exist. The `[ -f ... ]` guards cause them to skip gracefully. Consider cleaning these up as part of `matrix install` implementation or deferring to a follow-up.

7. **`pyproject.toml` hardware extras:** The comment now documents that `rpi-rgb-led-matrix` can be pip-installed from `git+https://github.com/hzeller/rpi-rgb-led-matrix`. `matrix install` could offer this as an option for Pi hardware users, or `matrix doctor` could suggest it when `rgbmatrix` import fails.
