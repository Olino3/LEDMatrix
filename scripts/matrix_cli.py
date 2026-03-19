#!/usr/bin/env python3
"""
matrix — LEDMatrix developer CLI.

"You take the red pill, you stay in Wonderland,
 and I show you how deep the rabbit hole goes."
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolved via the real path of this script so the /usr/local/bin/matrix
# symlink works from any directory.
LEDMATRIX_ROOT = Path(__file__).resolve().parent.parent

console = Console()

# Pi detection paths
_PI_DEV_MEM = Path("/dev/mem")
_PI_MODEL_PATH = Path("/proc/device-tree/model")

_venv_python = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"

if not _venv_python.exists():
    # Attempt to bootstrap automatically
    _uv = shutil.which("uv")
    if _uv:
        console.print("[yellow]No .venv found — running uv sync to bootstrap...[/yellow]")
        _result = subprocess.run([_uv, "sync", "--project", str(LEDMATRIX_ROOT)], check=False)
        if _result.returncode != 0:
            console.print("[red]uv sync failed. Run manually: uv sync[/red]")
            sys.exit(1)
    else:
        console.print(
            "[red]No .venv found and 'uv' is not installed.[/red]\n"
            "Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            "Then run:    uv sync"
        )
        sys.exit(1)

# After bootstrap (or if the venv already existed), ensure the Python binary exists and is executable.
if (not _venv_python.exists()) or (not os.access(_venv_python, os.X_OK)):
    console.print(
        "[red]The virtualenv Python interpreter was not found or is not executable at:"
        f" {_venv_python}[/red]\n"
        "This can happen if the requested Python version is not available on this system.\n"
        "Install the appropriate Python version and re-run: uv sync"
    )
    sys.exit(1)
PYTHON = str(_venv_python)

DEV_SETUP = LEDMATRIX_ROOT / "scripts" / "dev" / "dev_plugin_setup.sh"
PLUGINS_DIR = LEDMATRIX_ROOT / "plugins"
CONFIG_PATH = LEDMATRIX_ROOT / "config" / "config.json"

API_BASE = "http://localhost:5000/api/v3"
REGISTRY_URL = "https://raw.githubusercontent.com/ChuckBuilds/ledmatrix-plugins/main/plugins.json"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------


def print_banner() -> None:
    title = Text()
    title.append("░▒▓ MATRIX ▓▒░", style="bold green")
    title.append("  LED edition", style="dim green")
    quote = Text('"There is no spoon. There is only the display."', style="italic dim green")
    console.print(Panel.fit(Text.assemble(title, "\n", quote), border_style="green", padding=(0, 2)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list, **kwargs) -> int:
    return subprocess.run(cmd, **kwargs).returncode


def _dev_setup(*args) -> int:
    if not DEV_SETUP.exists():
        console.print(f"[red]dev_plugin_setup.sh not found at {DEV_SETUP}[/red]")
        return 1
    return _run(["bash", str(DEV_SETUP), *args], cwd=str(LEDMATRIX_ROOT))


def _read_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _write_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def _read_manifest(plugin_dir: Path) -> Optional[dict]:
    mf = plugin_dir / "manifest.json"
    if mf.exists():
        try:
            return json.loads(mf.read_text())
        except Exception:
            return None
    return None


def _to_class_name(plugin_id: str) -> str:
    return "".join(p.capitalize() for p in plugin_id.replace("_", "-").split("-")) + "Plugin"


def _to_display_name(plugin_id: str) -> str:
    return " ".join(p.capitalize() for p in plugin_id.replace("_", "-").split("-"))


def _detect_web() -> bool:
    try:
        requests.get(f"{API_BASE}/plugins/health", timeout=1)
        return True
    except Exception:
        return False


def _require_web() -> bool:
    """Print an error and return False if web interface is not running."""
    if not _detect_web():
        console.print(Panel(
            "[yellow]Web interface is not running.[/yellow]\n\n"
            "Start it in another terminal with:\n"
            "  [bold green]matrix web[/bold green]",
            title="[red]Service Unavailable[/red]",
            border_style="red",
        ))
        return False
    return True


def _is_raspberry_pi() -> bool:
    """Detect whether we are running on a Raspberry Pi."""
    if _PI_DEV_MEM.exists():
        return True
    if _PI_MODEL_PATH.exists():
        try:
            model = _PI_MODEL_PATH.read_text(errors="replace").lower()
            return "raspberry" in model
        except OSError:
            pass
    return False


# Apt packages required for a full Pi installation
_PI_APT_PACKAGES = [
    "python3-dev",
    "python3-pip",
    "python3-venv",
    "build-essential",
    "cython3",
    "scons",
    "cmake",
    "git",
    "curl",
]


def _run_install_script(script_name: str, *, use_sudo: bool = True) -> int:
    """Run a script from scripts/install/ and return its exit code."""
    script_path = LEDMATRIX_ROOT / "scripts" / "install" / script_name
    if not script_path.exists():
        console.print(f"[red]{script_name} not found at {script_path}[/red]")
        return 1
    cmd = ["sudo", "bash", str(script_path)] if use_sudo else ["bash", str(script_path)]
    return _run(cmd)


def _api_post(path: str, payload: dict) -> Optional[dict]:
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        return None


def _api_get(path: str) -> Optional[dict]:
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=10)
        return r.json()
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")
        return None


# ---------------------------------------------------------------------------
# Scaffold templates
# ---------------------------------------------------------------------------

SCHEMA_TEMPLATE = """\
{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "{name} Configuration",
  "properties": {{
    "enabled": {{
      "type": "boolean",
      "description": "Enable or disable the plugin",
      "default": true
    }},
    "display_duration": {{
      "type": "number",
      "description": "How long to display (seconds)",
      "default": 15,
      "minimum": 5,
      "maximum": 300
    }},
    "transition": {{
      "type": "object",
      "properties": {{
        "type": {{"type": "string", "enum": ["redraw", "fade", "slide", "wipe"], "default": "redraw"}},
        "speed": {{"type": "integer", "default": 2, "minimum": 1, "maximum": 10}},
        "enabled": {{"type": "boolean", "default": true}}
      }}
    }}
  }},
  "required": ["enabled"],
  "additionalProperties": false
}}
"""

MANAGER_TEMPLATE = '''\
from src.plugin_system.base_plugin import BasePlugin
from typing import Any, Dict


class {class_name}(BasePlugin):
    """Plugin: {name}."""

    def __init__(
        self,
        plugin_id: str,
        config: Dict[str, Any],
        display_manager: Any,
        cache_manager: Any,
        plugin_manager: Any,
    ) -> None:
        super().__init__(plugin_id, config, display_manager, cache_manager, plugin_manager)

    def update(self) -> None:
        self.logger.debug("{id}: update() called")

    def display(self, force_clear: bool = False) -> None:
        self.logger.debug("{id}: display() called — %dx%d",
                          self.display_manager.width, self.display_manager.height)
        self.display_manager.clear()

    def validate_config(self) -> bool:
        return super().validate_config()

    def on_config_change(self, new_config: Dict[str, Any]) -> None:
        super().on_config_change(new_config)
'''

GITIGNORE_CONTENT = "__pycache__/\n*.py[cod]\n*.egg-info/\n.dependencies_installed\n.env\n"
REQUIREMENTS_CONTENT = "# Add plugin dependencies here, e.g.:\n# requests>=2.28.0\n"

# ---------------------------------------------------------------------------
# CLI root
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    \b
    LEDMatrix developer CLI.
    "Wake up, Neo."
    """
    print_banner()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# matrix run
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--debug", is_flag=True, help="Enable verbose debug logging.")
def run(debug: bool) -> None:
    """Start the LED display in emulator mode."""
    flags = ["--debug"] if debug else []
    env = {**os.environ, "EMULATOR": "true"}
    console.print(Rule("[green]display[/green]"))
    console.print(f"  [dim]root:[/dim] {LEDMATRIX_ROOT}")
    sys.exit(_run([PYTHON, str(LEDMATRIX_ROOT / "run.py"), *flags], env=env))


# ---------------------------------------------------------------------------
# matrix web
# ---------------------------------------------------------------------------

@cli.command()
def web() -> None:
    """Start the web interface on localhost:5000."""
    console.print(Rule("[green]web interface[/green]"))
    console.print("  [dim]http://localhost:5000[/dim]")
    sys.exit(_run([PYTHON, str(LEDMATRIX_ROOT / "web_interface" / "start.py")]))


# ---------------------------------------------------------------------------
# matrix setup
# ---------------------------------------------------------------------------

def _sync_venv(extras: tuple) -> int:
    """Sync the .venv using uv. Returns the return code (0 = success)."""
    uv = shutil.which("uv")
    if not uv:
        console.print("[red]'uv' not found. Install it:[/red]")
        console.print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        return 1

    extras_flags = []
    for extra in extras:
        extras_flags += ["--extra", extra]

    console.print(f"  Syncing deps with extras: {', '.join(extras) or 'none'}")
    rc = _run([uv, "sync", *extras_flags], cwd=str(LEDMATRIX_ROOT))
    if rc == 0:
        console.print("[green]\u2713 .venv is ready[/green]")
    return rc


@cli.command()
@click.option("--extras", multiple=True, default=("emulator",),
              show_default=True, help="uv extras to install (repeatable).")
def setup(extras: tuple) -> None:
    """Create or sync the .venv using uv. Run this after cloning or pulling."""
    console.print(Rule("[green]setup[/green]"))
    sys.exit(_sync_venv(extras))


# ---------------------------------------------------------------------------
# Hardware (rgbmatrix C-extension) helper
# ---------------------------------------------------------------------------

_RGBMATRIX_APT_DEPS = ["python3-dev", "gcc", "make"]

_RGBMATRIX_PIP_URL = (
    "git+https://github.com/hzeller/rpi-rgb-led-matrix@master"
    "#subdirectory=bindings/python"
)


def _install_rgbmatrix_hardware() -> None:
    """Build and install the rgbmatrix C-extension from source."""
    arch = platform.machine()
    if not (arch.startswith("aarch64") or arch.startswith("arm")):
        console.print(
            f"[red]--hardware requires an ARM platform (detected: {arch})[/red]\n"
            "The rgbmatrix C-extension can only be built on Raspberry Pi / ARM boards."
        )
        sys.exit(1)

    # Check required apt packages
    missing: list[str] = []
    for pkg in _RGBMATRIX_APT_DEPS:
        result = subprocess.run(
            ["dpkg", "-l", pkg], capture_output=True, check=False,
        )
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        console.print(
            f"[red]Missing build dependencies: {', '.join(missing)}[/red]\n"
            f"Install them with:  [bold]sudo apt install {' '.join(missing)}[/bold]"
        )
        sys.exit(1)

    # Build rgbmatrix via uv pip
    uv = shutil.which("uv")
    if not uv:
        console.print("[red]'uv' not found. Install it:[/red]")
        console.print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)

    console.print("  Building rgbmatrix C-extension (this may take a few minutes)...")
    with console.status("[bold green]Compiling rgbmatrix...", spinner="dots"):
        result = subprocess.run(
            [uv, "pip", "install", "--project", str(LEDMATRIX_ROOT), _RGBMATRIX_PIP_URL],
            capture_output=True, text=True,
        )

    if result.returncode != 0:
        console.print("[red]rgbmatrix build failed![/red]")
        if result.stderr:
            console.print(f"[dim]{result.stderr[:500]}[/dim]")
        console.print(
            "\nTroubleshooting:\n"
            "  1. Ensure build tools are installed: sudo apt install python3-dev gcc make\n"
            "  2. Check you have enough disk space and memory\n"
            "  3. Try running manually:\n"
            f"     uv pip install --project {LEDMATRIX_ROOT} {_RGBMATRIX_PIP_URL}"
        )
        sys.exit(result.returncode)

    console.print("[green]✓ rgbmatrix C-extension installed[/green]")
    console.print("  Run [bold]matrix doctor[/bold] to verify the installation.")


# ---------------------------------------------------------------------------
# matrix install
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--no-services", is_flag=True, help="Skip systemd service installation.")
@click.option("--emulator", is_flag=True, help="Install emulator extras instead of hardware.")
@click.option("--permissions", is_flag=True, help="Set up cache directory, file permissions, and sudoers rules (Pi only).")
@click.option("--services", "extra_services", is_flag=True, help="Install web interface and WiFi monitor services (Pi only).")
@click.option("--prerequisites", is_flag=True, help="Install required apt packages (Pi only).")
@click.option("--hardware", is_flag=True, help="Install rgbmatrix C-extension (Pi only).")
def install(no_services: bool, emulator: bool, permissions: bool,
            extra_services: bool, prerequisites: bool, hardware: bool) -> None:
    """Full installation: sync deps and optionally install systemd services.

    Pi-specific flags (--permissions, --services, --prerequisites, --hardware)
    are no-ops on non-Pi platforms.
    """
    console.print(Rule("[green]install[/green]"))

    is_pi = _is_raspberry_pi()
    pi_flags_requested = permissions or extra_services or prerequisites

    # Step 0: Prerequisites (apt packages, Pi only)
    if prerequisites:
        if is_pi:
            console.print("  Installing system prerequisites (may prompt for sudo)...")
            rc = _run(["sudo", "apt-get", "update", "-qq"])
            if rc != 0:
                console.print("[yellow]\u26a0 apt-get update failed — continuing anyway[/yellow]")
            rc = _run(["sudo", "apt-get", "install", "-y", "-qq"] + _PI_APT_PACKAGES)
            if rc == 0:
                console.print("[green]\u2713 System prerequisites installed[/green]")
            else:
                console.print("[red]apt-get install failed[/red]")
                sys.exit(rc)
        else:
            console.print("[dim]Skipping prerequisites — not a Raspberry Pi[/dim]")

    # Step 1: Setup venv
    extras = ("emulator",) if emulator else ()
    rc = _sync_venv(extras)
    if rc != 0:
        sys.exit(rc)

    # Step 2: Ensure config.json exists
    config_template = LEDMATRIX_ROOT / "config" / "config.template.json"
    config_file = LEDMATRIX_ROOT / "config" / "config.json"
    if not config_file.exists() and config_template.exists():
        shutil.copy(config_template, config_file)
        console.print("[green]\u2713 Created config/config.json from template[/green]")
    elif config_file.exists():
        console.print("[dim]config/config.json already exists \u2014 skipping[/dim]")
    else:
        console.print("[yellow]\u26a0 No config template found \u2014 create config/config.json manually[/yellow]")

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
        console.print("[green]\u2713 Services installed[/green]")

    # Step 4: Permissions (Pi only)
    if permissions:
        if is_pi:
            console.print("  Setting up permissions (may prompt for sudo)...")
            perm_scripts = [
                ("setup_cache.sh", "Cache directory"),
                ("configure_web_sudo.sh", "Web sudoers"),
                ("configure_wifi_permissions.sh", "WiFi permissions"),
            ]
            for script, label in perm_scripts:
                rc = _run_install_script(script)
                if rc == 0:
                    console.print(f"[green]\u2713 {label} configured[/green]")
                else:
                    console.print(f"[yellow]\u26a0 {label} setup failed (exit {rc})[/yellow]")
        else:
            console.print("[dim]Skipping permissions — not a Raspberry Pi[/dim]")

    # Step 5: Extra services — web + WiFi monitor (Pi only)
    if extra_services:
        if is_pi:
            console.print("  Installing additional services (may prompt for sudo)...")
            svc_scripts = [
                ("install_web_service.sh", "Web service"),
                ("install_wifi_monitor.sh", "WiFi monitor service"),
            ]
            for script, label in svc_scripts:
                rc = _run_install_script(script)
                if rc == 0:
                    console.print(f"[green]\u2713 {label} installed[/green]")
                else:
                    console.print(f"[yellow]\u26a0 {label} installation failed (exit {rc})[/yellow]")
        else:
            console.print("[dim]Skipping extra services — not a Raspberry Pi[/dim]")

    # Step 6: Hardware — build rgbmatrix C-extension (ARM only)
    if hardware:
        _install_rgbmatrix_hardware()

    console.print(Panel("[green]Installation complete![/green]\n\nRun [bold]matrix doctor[/bold] to verify.", border_style="green"))


# ---------------------------------------------------------------------------
# matrix doctor
# ---------------------------------------------------------------------------

@cli.command()
def doctor() -> None:
    """Check system health: venv, config, services, hardware."""
    console.print(Rule("[green]doctor[/green]"))
    rows: list[tuple[str, str, str]] = []  # (check_name, status_icon, detail)
    any_fail = False

    def ok(name: str, detail: str = "") -> None:
        rows.append((name, "[green]\u2713 PASS[/green]", detail))

    def warn(name: str, detail: str = "") -> None:
        rows.append((name, "[yellow]\u26a0 WARN[/yellow]", detail))

    def fail(name: str, detail: str = "") -> None:
        nonlocal any_fail
        any_fail = True
        rows.append((name, "[red]\u2717 FAIL[/red]", detail))

    # --- uv ---
    uv_path = shutil.which("uv")
    if uv_path:
        ok("uv installed", uv_path)
    else:
        fail("uv installed", "Not found \u2014 run: curl -LsSf https://astral.sh/uv/install.sh | sh")

    # --- venv ---
    venv_py = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        result = subprocess.run([str(venv_py), "-c", "import PIL; print(PIL.__version__)"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            ok(".venv / Pillow", f"Pillow {result.stdout.strip()}")
        else:
            fail(".venv / Pillow", "Pillow import failed \u2014 run: matrix setup")
    else:
        fail(".venv", f"Not found at {venv_py} \u2014 run: matrix setup")

    # --- config.json ---
    cfg = LEDMATRIX_ROOT / "config" / "config.json"
    if cfg.exists():
        ok("config/config.json", str(cfg))
    else:
        fail("config/config.json", "Missing \u2014 run: matrix install  (or copy from config.template.json)")

    # --- config_secrets.json ---
    secrets = LEDMATRIX_ROOT / "config" / "config_secrets.json"
    if secrets.exists():
        ok("config/config_secrets.json", str(secrets))
    else:
        warn("config/config_secrets.json", "Missing \u2014 plugins needing API keys will error")

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
        unit_file = Path(f"/etc/systemd/system/{unit}.service")
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
    dev_mem = Path("/dev/mem")
    emulator_env = os.environ.get("EMULATOR", "").lower() in ("1", "true", "yes")
    if dev_mem.exists():
        ok("Hardware (/dev/mem)", "Pi hardware detected")
    elif emulator_env:
        ok("Emulator mode", "EMULATOR=true set")
    else:
        warn("Hardware", "/dev/mem not found and EMULATOR not set \u2014 set EMULATOR=true for dev")

    # --- rgbmatrix (Pi hardware only) ---
    if dev_mem.exists() and not emulator_env and venv_py.exists():
        result = subprocess.run(
            [str(venv_py), "-c", "import rgbmatrix; print('ok')"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            ok("rgbmatrix", "C extension importable")
        else:
            warn("rgbmatrix", "Not installed \u2014 display will fail without EMULATOR=true")

    # --- Python version ---
    if venv_py.exists():
        ver_result = subprocess.run(
            [str(venv_py), "-c", "import platform; print(platform.python_version())"],
            capture_output=True, text=True,
        )
        py_ver = ver_result.stdout.strip() if ver_result.returncode == 0 else platform.python_version()
    else:
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


# ---------------------------------------------------------------------------
# matrix logs
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--service", type=click.Choice(["display", "web", "all"]), default="display",
              show_default=True, help="Which service log to tail.")
def logs(service: str) -> None:
    """Tail live service logs (Raspberry Pi / systemd only)."""
    services = {
        "display": ["ledmatrix"],
        "web": ["ledmatrix-web"],
        "all": ["ledmatrix", "ledmatrix-web"],
    }
    units = services[service]
    cmd = ["journalctl", "-f", "--no-pager"] + [f"-u{u}" for u in units]
    console.print(Rule(f"[green]logs — {service}[/green]"))
    try:
        sys.exit(_run(cmd))
    except FileNotFoundError:
        console.print("[yellow]journalctl not found — not running on a systemd host.[/yellow]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# matrix service
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("action", type=click.Choice(["start", "stop", "restart", "status"]))
@click.option("--service", type=click.Choice(["display", "web", "all"]), default="display",
              show_default=True, help="Which service to act on.")
def service(action: str, service: str) -> None:
    """Manage LEDMatrix systemd services (Raspberry Pi only)."""
    service_map = {
        "display": ["ledmatrix"],
        "web": ["ledmatrix-web"],
        "all": ["ledmatrix", "ledmatrix-web"],
    }
    units = service_map[service]
    console.print(Rule(f"[green]service {action} — {service}[/green]"))
    try:
        rc = 0
        for unit in units:
            rc |= _run(["sudo", "systemctl", action, unit])
        sys.exit(rc)
    except FileNotFoundError:
        console.print("[yellow]systemctl not found — not running on a systemd host.[/yellow]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# matrix plugin (group)
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def plugin(ctx: click.Context) -> None:
    """Plugin management — scaffold, install, link, inspect."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# matrix plugin new
# ---------------------------------------------------------------------------

CATEGORIES = ["sports", "time", "weather", "transportation", "finance", "system", "media", "other"]


@plugin.command("new")
@click.argument("id")
@click.option("--path", "dest", default=None, help="Parent directory (default: cwd).")
@click.option("--no-interactive", is_flag=True, help="Skip prompts; use derived defaults.")
def plugin_new(id: str, dest: Optional[str], no_interactive: bool) -> None:
    """Scaffold a new plugin with all required files.

    Prompts for author, description, category, and tags unless
    --no-interactive is set.
    """
    plugin_id = id
    base_path = Path(dest).resolve() if dest else Path.cwd()
    plugin_dir = base_path / plugin_id

    if plugin_dir.exists():
        console.print(f"[red]Directory already exists:[/red] {plugin_dir}")
        sys.exit(1)

    display_name = _to_display_name(plugin_id)
    class_name = _to_class_name(plugin_id)

    console.print(Rule(f"[green]new plugin — {plugin_id}[/green]"))

    if not no_interactive:
        display_name = click.prompt("  Display name", default=display_name)
        author      = click.prompt("  Author", default="")
        description = click.prompt("  Description", default="")
        category    = click.prompt(
            "  Category",
            type=click.Choice(CATEGORIES),
            default="other",
            show_choices=True,
        )
        tags_raw    = click.prompt("  Tags (comma-separated)", default="")
        tags        = [t.strip() for t in tags_raw.split(",") if t.strip()]
        update_interval = click.prompt("  Update interval (seconds)", default=60, type=int)
    else:
        author = ""
        description = ""
        category = "other"
        tags = []
        update_interval = 60

    plugin_dir.mkdir(parents=True)

    # manifest.json
    manifest = {
        "id": plugin_id,
        "name": display_name,
        "version": "0.1.0",
        "author": author,
        "description": description,
        "entry_point": "manager.py",
        "class_name": class_name,
        "category": category,
        "tags": tags,
        "display_modes": [plugin_id],
        "update_interval": update_interval,
        "default_duration": 15,
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # config_schema.json
    (plugin_dir / "config_schema.json").write_text(SCHEMA_TEMPLATE.format(name=display_name))

    # manager.py
    (plugin_dir / "manager.py").write_text(
        MANAGER_TEMPLATE.format(id=plugin_id, name=display_name, class_name=class_name)
    )

    # requirements.txt + .gitignore
    (plugin_dir / "requirements.txt").write_text(REQUIREMENTS_CONTENT)
    (plugin_dir / ".gitignore").write_text(GITIGNORE_CONTENT)

    # git init
    _run(["git", "init", "-b", "main", str(plugin_dir)],
         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # pre-push hook
    hook_src = LEDMATRIX_ROOT / "scripts" / "git-hooks" / "pre-push-plugin-version"
    hooks_dir = plugin_dir / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    if hook_src.exists():
        shutil.copy(hook_src, hooks_dir / "pre-push")
        (hooks_dir / "pre-push").chmod(0o755)

    # Summary table
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("id",       plugin_id)
    t.add_row("class",    class_name)
    t.add_row("category", category)
    t.add_row("location", str(plugin_dir))
    console.print(Panel(t, title="[green]created[/green]", border_style="green"))

    console.print(f"\n  [dim]Next:[/dim]  matrix plugin link [bold]{plugin_id}[/bold] {plugin_dir}\n")


# ---------------------------------------------------------------------------
# matrix plugin link / unlink / status
# ---------------------------------------------------------------------------

@plugin.command("link")
@click.argument("id")
@click.argument("path")
def plugin_link(id: str, path: str) -> None:
    """Link a local plugin repo into the display runtime."""
    console.print(Rule(f"[green]link — {id}[/green]"))
    sys.exit(_dev_setup("link", id, path))


@plugin.command("unlink")
@click.argument("id")
def plugin_unlink(id: str) -> None:
    """Remove a dev plugin symlink (preserves the repo)."""
    console.print(Rule(f"[green]unlink — {id}[/green]"))
    sys.exit(_dev_setup("unlink", id))


@plugin.command("status")
def plugin_status() -> None:
    """Show git status of all linked plugin repos."""
    console.print(Rule("[green]plugin repo status[/green]"))
    sys.exit(_dev_setup("status"))


# ---------------------------------------------------------------------------
# matrix plugin list
# ---------------------------------------------------------------------------

@plugin.command("list")
def plugin_list() -> None:
    """Rich table of all installed plugins and their state."""
    console.print(Rule("[green]installed plugins[/green]"))

    config = _read_config()
    plugin_dirs = sorted(p for p in PLUGINS_DIR.iterdir() if p.is_dir() or p.is_symlink())

    if not plugin_dirs:
        console.print("  [dim]No plugins found in plugins/[/dim]")
        return

    t = Table(show_header=True, header_style="bold green", border_style="dim")
    t.add_column("Plugin", min_width=20)
    t.add_column("Status", min_width=10)
    t.add_column("Version", min_width=8)
    t.add_column("Category", min_width=12)
    t.add_column("Dev link", min_width=6)

    for p in plugin_dirs:
        mf = _read_manifest(p)
        if mf is None:
            continue
        pid      = mf.get("id", p.name)
        version  = mf.get("version", "—")
        category = mf.get("category", "—")
        enabled  = config.get(pid, {}).get("enabled", True)
        is_link  = p.is_symlink()

        status_text = Text("enabled", style="green") if enabled else Text("disabled", style="dim")
        link_text   = Text("yes", style="cyan") if is_link else Text("no", style="dim")

        t.add_row(pid, status_text, version, category, link_text)

    console.print(t)


# ---------------------------------------------------------------------------
# matrix plugin render
# ---------------------------------------------------------------------------

@plugin.command("render")
@click.argument("id")
@click.option("--output", "-o", default=None, help="Output PNG path.")
@click.option("--width",  default=None, type=int, help="Display width in pixels.")
@click.option("--height", default=None, type=int, help="Display height in pixels.")
@click.option("--skip-update", is_flag=True, help="Skip update(), render display only.")
def plugin_render(id: str, output: Optional[str], width: Optional[int],
                  height: Optional[int], skip_update: bool) -> None:
    """Render a plugin to PNG without running the full display loop."""
    render_script = LEDMATRIX_ROOT / "scripts" / "render_plugin.py"
    if not render_script.exists():
        console.print(f"[red]render_plugin.py not found at {render_script}[/red]")
        sys.exit(1)

    cmd = [PYTHON, str(render_script), "--plugin", id]
    if output:     cmd += ["--output", output]
    if width:      cmd += ["--width",  str(width)]
    if height:     cmd += ["--height", str(height)]
    if skip_update: cmd += ["--skip-update"]

    console.print(Rule(f"[green]render — {id}[/green]"))
    out_path = output or "/tmp/plugin_render.png"
    console.print(f"  [dim]output:[/dim] {out_path}")
    sys.exit(_run(cmd, cwd=str(LEDMATRIX_ROOT)))


# ---------------------------------------------------------------------------
# matrix plugin install
# ---------------------------------------------------------------------------

@plugin.command("install")
@click.argument("target")
@click.option("--branch", default=None, help="Git branch to install from.")
def plugin_install(target: str, branch: Optional[str]) -> None:
    """Install a plugin from the store or a GitHub URL.

    TARGET can be a plugin ID (e.g. clock-simple) or a full GitHub URL.
    """
    if not _require_web():
        sys.exit(1)

    console.print(Rule(f"[green]install — {target}[/green]"))

    is_url = target.startswith("http") or "github.com" in target

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=True) as progress:
        progress.add_task("Installing...", total=None)
        if is_url:
            result = _api_post("/plugins/install-from-url",
                               {"repo_url": target, **({"branch": branch} if branch else {})})
        else:
            result = _api_post("/plugins/install",
                               {"plugin_id": target, **({"branch": branch} if branch else {})})

    if result is None:
        sys.exit(1)

    if result.get("success") or result.get("status") == "success":
        pid = result.get("plugin_id", target)
        console.print(f"  [green]Installed:[/green] [bold]{pid}[/bold]")
    else:
        msg = result.get("error") or result.get("message") or str(result)
        console.print(f"  [red]Install failed:[/red] {msg}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# matrix plugin uninstall
# ---------------------------------------------------------------------------

@plugin.command("uninstall")
@click.argument("id")
@click.option("--keep-config", is_flag=True,
              help="Preserve the plugin's config.json entry after removal.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def plugin_uninstall(id: str, keep_config: bool, yes: bool) -> None:
    """Uninstall a plugin. Prompts for confirmation."""
    if not _require_web():
        sys.exit(1)

    if not yes:
        click.confirm(f"  Uninstall [bold]{id}[/bold]? This cannot be undone.", abort=True)

    console.print(Rule(f"[green]uninstall — {id}[/green]"))

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console, transient=True) as progress:
        progress.add_task("Uninstalling...", total=None)
        result = _api_post("/plugins/uninstall",
                           {"plugin_id": id, "preserve_config": keep_config})

    if result is None:
        sys.exit(1)

    if result.get("success") or result.get("status") == "success":
        console.print(f"  [green]Uninstalled:[/green] [bold]{id}[/bold]")
    else:
        msg = result.get("error") or result.get("message") or str(result)
        console.print(f"  [red]Uninstall failed:[/red] {msg}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# matrix plugin update
# ---------------------------------------------------------------------------

@plugin.command("update")
@click.argument("id", required=False, default=None)
def plugin_update(id: Optional[str]) -> None:
    """Update a plugin, or all plugins if no ID is given."""
    if not _require_web():
        sys.exit(1)

    if id:
        targets = [id]
    else:
        # Discover all installed plugin IDs from plugins dir
        targets = sorted(
            m["id"]
            for p in PLUGINS_DIR.iterdir()
            if (p.is_dir() or p.is_symlink()) and (m := _read_manifest(p))
        )

    console.print(Rule("[green]update[/green]"))

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Updating plugins...", total=len(targets))
        results = []
        for pid in targets:
            progress.update(task, description=f"Updating [bold]{pid}[/bold]...")
            r = _api_post("/plugins/update", {"plugin_id": pid})
            results.append((pid, r))
            progress.advance(task)

    t = Table(show_header=True, header_style="bold green", border_style="dim")
    t.add_column("Plugin", min_width=20)
    t.add_column("Result")

    for pid, r in results:
        if r is None:
            t.add_row(pid, Text("error", style="red"))
        elif r.get("success") or r.get("status") == "success":
            t.add_row(pid, Text("updated", style="green"))
        else:
            msg = r.get("message") or r.get("error") or "failed"
            t.add_row(pid, Text(msg, style="yellow"))

    console.print(t)


# ---------------------------------------------------------------------------
# matrix plugin enable / disable
# ---------------------------------------------------------------------------

@plugin.command("enable")
@click.argument("id")
def plugin_enable(id: str) -> None:
    """Enable a plugin (edits config directly — no service required)."""
    _toggle_plugin(id, enabled=True)


@plugin.command("disable")
@click.argument("id")
def plugin_disable(id: str) -> None:
    """Disable a plugin (edits config directly — no service required)."""
    _toggle_plugin(id, enabled=False)


def _toggle_plugin(plugin_id: str, enabled: bool) -> None:
    action = "enable" if enabled else "disable"
    console.print(Rule(f"[green]{action} — {plugin_id}[/green]"))

    config = _read_config()
    if plugin_id not in config:
        config[plugin_id] = {}
    config[plugin_id]["enabled"] = enabled
    _write_config(config)

    state = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
    console.print(f"  [bold]{plugin_id}[/bold] → {state}")
    console.print(f"  [dim]Takes effect on next display loop cycle.[/dim]")


# ---------------------------------------------------------------------------
# matrix plugin health
# ---------------------------------------------------------------------------

@plugin.command("health")
@click.argument("id", required=False, default=None)
def plugin_health(id: Optional[str]) -> None:
    """Show runtime plugin health. Requires the web interface to be running."""
    if not _require_web():
        sys.exit(1)

    console.print(Rule("[green]plugin health[/green]"))

    path = f"/plugins/health/{id}" if id else "/plugins/health"
    data = _api_get(path)
    if data is None:
        sys.exit(1)

    # Normalise — single plugin returns a dict, all plugins returns a list or dict
    if isinstance(data, dict) and "plugins" in data:
        entries = data["plugins"]
    elif isinstance(data, dict) and "plugin_id" in data:
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        entries = [data]

    t = Table(show_header=True, header_style="bold green", border_style="dim")
    t.add_column("Plugin", min_width=20)
    t.add_column("State", min_width=10)
    t.add_column("Errors", min_width=7, justify="right")
    t.add_column("Last error", min_width=40)

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pid        = entry.get("plugin_id") or entry.get("id", "—")
        state      = entry.get("state", "—")
        error_cnt  = str(entry.get("error_count", 0))
        last_error = (entry.get("last_error") or "—")[:60]

        if state in ("running", "enabled"):
            state_text = Text(state, style="green")
        elif state in ("errored", "error"):
            state_text = Text(state, style="red")
        else:
            state_text = Text(state, style="dim")

        t.add_row(pid, state_text, error_cnt, last_error)

    console.print(t)


# ---------------------------------------------------------------------------
# matrix plugin store
# ---------------------------------------------------------------------------

@plugin.command("store")
@click.argument("query", required=False, default=None)
def plugin_store(query: Optional[str]) -> None:
    """Browse the plugin store. Optionally filter by name or tag."""
    console.print(Rule("[green]plugin store[/green]"))

    with Progress(SpinnerColumn(), TextColumn("Fetching registry..."),
                  console=console, transient=True) as progress:
        progress.add_task("", total=None)
        try:
            resp = requests.get(REGISTRY_URL, timeout=10)
            resp.raise_for_status()
            registry = resp.json()
        except Exception as e:
            console.print(f"[red]Could not fetch registry:[/red] {e}")
            sys.exit(1)

    plugins = registry.get("plugins", [])

    if query:
        q = query.lower()
        plugins = [
            p for p in plugins
            if q in p.get("name", "").lower()
            or q in p.get("id", "").lower()
            or any(q in tag.lower() for tag in p.get("tags", []))
            or q in p.get("category", "").lower()
        ]

    if not plugins:
        match_msg = f' matching "{query}"' if query else ''
        console.print(f"  [dim]No plugins found{match_msg}.[/dim]")
        return

    # Mark locally installed plugins
    installed_ids = {
        _read_manifest(p).get("id")
        for p in PLUGINS_DIR.iterdir()
        if (p.is_dir() or p.is_symlink()) and _read_manifest(p)
    }

    t = Table(show_header=True, header_style="bold green", border_style="dim")
    t.add_column("Plugin", min_width=22)
    t.add_column("Author", min_width=14)
    t.add_column("Category", min_width=14)
    t.add_column("Version", min_width=8)
    t.add_column("Verified", min_width=9, justify="center")
    t.add_column("Installed", min_width=10, justify="center")

    for p in sorted(plugins, key=lambda x: x.get("name", "")):
        pid       = p.get("id", "—")
        name      = p.get("name", pid)
        author    = p.get("author", "—")
        category  = p.get("category", "—")
        version   = p.get("latest_version", "—")
        verified  = Text("✓", style="green") if p.get("verified") else Text("✗", style="dim")
        inst_text = Text("✓", style="cyan") if pid in installed_ids else Text("—", style="dim")

        t.add_row(name, author, category, version, verified, inst_text)

    console.print(t)
    if query:
        console.print(f"  [dim]{len(plugins)} result(s) for \"{query}\"[/dim]\n")
    else:
        console.print(f"  [dim]{len(plugins)} plugins in registry[/dim]\n")


# ---------------------------------------------------------------------------
# matrix diagnose
# ---------------------------------------------------------------------------

@cli.group()
def diagnose() -> None:
    """Run diagnostic checks on LEDMatrix components."""
    pass


# -- diagnose helpers -------------------------------------------------------

class _DiagResult:
    """Accumulator for diagnostic check results."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def ok(self, name: str, detail: str = "") -> None:
        self.rows.append((name, "[green]✓ PASS[/green]", detail))
        self.passed += 1

    def warn(self, name: str, detail: str = "") -> None:
        self.rows.append((name, "[yellow]⚠ WARN[/yellow]", detail))
        self.warnings += 1

    def fail(self, name: str, detail: str = "") -> None:
        self.rows.append((name, "[red]✗ FAIL[/red]", detail))
        self.failed += 1

    def render(self, title: str) -> None:
        """Print a Rich table with results and a summary line."""
        table = Table(title=title, show_header=True, header_style="bold")
        table.add_column("Check", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Detail", style="dim")
        for name, status, detail in self.rows:
            table.add_row(name, status, detail)
        console.print(table)
        summary_parts = [
            f"[green]{self.passed} passed[/green]",
            f"[red]{self.failed} failed[/red]",
            f"[yellow]{self.warnings} warning(s)[/yellow]",
        ]
        console.print("  " + "  |  ".join(summary_parts) + "\n")


def _check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to *host*:*port* succeeds."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check_url(url: str, timeout: float = 3.0) -> Optional[int]:
    """Return the HTTP status code or None on failure."""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code
    except Exception:
        return None


# -- diagnose web -----------------------------------------------------------

@diagnose.command("web")
def diagnose_web() -> None:
    """Check web interface health: process, port, API, static assets."""
    console.print(Rule("[green]diagnose web[/green]"))
    r = _DiagResult()

    # 1. Flask process — look for a process listening on port 5000
    if _check_port_open("127.0.0.1", 5000):
        r.ok("Port 5000 reachable", "Something is listening on localhost:5000")
    else:
        r.fail("Port 5000 reachable", "Nothing listening on localhost:5000")

    # 2. API status endpoint
    status_code = _check_url(f"{API_BASE}/status")
    if status_code is not None and 200 <= status_code < 400:
        r.ok("/api/v3/status responds", f"HTTP {status_code}")
    elif status_code is not None:
        r.warn("/api/v3/status responds", f"HTTP {status_code}")
    else:
        r.fail("/api/v3/status responds", "No response (is the web interface running?)")

    # 3. Plugin health endpoint
    health_code = _check_url(f"{API_BASE}/plugins/health")
    if health_code is not None and 200 <= health_code < 400:
        r.ok("/api/v3/plugins/health", f"HTTP {health_code}")
    elif health_code is not None:
        r.warn("/api/v3/plugins/health", f"HTTP {health_code}")
    else:
        r.fail("/api/v3/plugins/health", "No response")

    # 4. Required web interface files
    required_files = [
        "web_interface/app.py",
        "web_interface/start.py",
        "web_interface/blueprints/api_v3.py",
        "web_interface/blueprints/pages_v3.py",
    ]
    for rel in required_files:
        fp = LEDMATRIX_ROOT / rel
        if fp.exists():
            r.ok(f"File: {rel}")
        else:
            r.fail(f"File: {rel}", "MISSING")

    # 5. Static assets directory
    static_dir = LEDMATRIX_ROOT / "web_interface" / "static"
    if static_dir.is_dir():
        asset_count = sum(1 for _ in static_dir.rglob("*") if _.is_file())
        r.ok("Static assets directory", f"{asset_count} file(s)")
    else:
        r.warn("Static assets directory", "web_interface/static/ not found")

    # 6. Templates directory
    templates_dir = LEDMATRIX_ROOT / "web_interface" / "templates"
    if templates_dir.is_dir():
        tpl_count = sum(1 for _ in templates_dir.rglob("*.html"))
        r.ok("Templates directory", f"{tpl_count} template(s)")
    else:
        r.warn("Templates directory", "web_interface/templates/ not found")

    # 7. Config — web_display_autostart
    cfg = _read_config()
    autostart = cfg.get("web_display_autostart", None)
    if autostart is True:
        r.ok("web_display_autostart", "true")
    elif autostart is False:
        r.warn("web_display_autostart", "false — web UI will not auto-start")
    else:
        r.warn("web_display_autostart", "not set in config.json")

    # 8. systemd service (Pi only)
    svc_file = Path("/etc/systemd/system/ledmatrix-web.service")
    if svc_file.exists():
        result = subprocess.run(
            ["systemctl", "is-active", "ledmatrix-web"],
            capture_output=True, text=True,
        )
        status = result.stdout.strip()
        if status == "active":
            r.ok("ledmatrix-web.service", "active")
        else:
            r.warn("ledmatrix-web.service", f"status: {status}")
    else:
        r.warn("ledmatrix-web.service", "Not installed (OK on dev machine)")

    r.render("Web Interface Diagnostics")

    if r.failed > 0:
        console.print("[dim]Hint: start the web interface with[/dim]  [bold]matrix web[/bold]\n")


# -- diagnose network -------------------------------------------------------

@diagnose.command("network")
def diagnose_network() -> None:
    """Check network connectivity: internet, DNS, WiFi signal (Pi only)."""
    console.print(Rule("[green]diagnose network[/green]"))
    r = _DiagResult()

    # 1. Internet connectivity — ping 8.8.8.8
    ping_result = subprocess.run(
        ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
        capture_output=True, text=True,
    )
    if ping_result.returncode == 0:
        r.ok("Internet (ping 8.8.8.8)", "Reachable")
    else:
        r.fail("Internet (ping 8.8.8.8)", "Unreachable")

    # 2. DNS resolution
    import socket as _socket
    try:
        addr = _socket.getaddrinfo("pypi.org", 443, proto=_socket.IPPROTO_TCP)
        if addr:
            r.ok("DNS resolution (pypi.org)", addr[0][4][0])
        else:
            r.fail("DNS resolution (pypi.org)", "No results")
    except _socket.gaierror as exc:
        r.fail("DNS resolution (pypi.org)", str(exc))

    # 3. Captive portal detection — expect 204 from connectivity check URLs
    portal_urls = [
        ("http://connectivitycheck.gstatic.com/generate_204", 204),
        ("http://detectportal.firefox.com/canonical.html", 200),
    ]
    for url, expected in portal_urls:
        code = _check_url(url, timeout=5.0)
        if code == expected:
            r.ok(f"No captive portal ({url.split('/')[2]})")
        elif code is not None:
            r.warn(f"Possible captive portal ({url.split('/')[2]})", f"HTTP {code} (expected {expected})")
        else:
            r.warn(f"Captive portal check ({url.split('/')[2]})", "No response")

    # 4. WiFi signal strength (Pi only)
    if _is_raspberry_pi():
        iwconfig_result = subprocess.run(
            ["iwconfig", "wlan0"], capture_output=True, text=True,
        )
        if iwconfig_result.returncode == 0:
            output = iwconfig_result.stdout
            import re
            essid_match = re.search(r'ESSID:"([^"]*)"', output)
            signal_match = re.search(r"Signal level[=:](-?\d+)", output)
            quality_match = re.search(r"Link Quality[=:](\S+)", output)

            if essid_match and essid_match.group(1):
                r.ok("WiFi SSID", essid_match.group(1))
            else:
                r.warn("WiFi SSID", "Not connected or ESSID not found")

            if signal_match:
                level = int(signal_match.group(1))
                if level > -50:
                    r.ok("WiFi signal", f"{level} dBm (excellent)")
                elif level > -70:
                    r.ok("WiFi signal", f"{level} dBm (good)")
                else:
                    r.warn("WiFi signal", f"{level} dBm (weak)")
            elif quality_match:
                r.ok("WiFi link quality", quality_match.group(1))
        else:
            r.warn("WiFi diagnostics", "iwconfig failed (no wlan0 or iwconfig not installed)")

        # 5. WiFi monitor service (Pi only)
        svc_file = Path("/etc/systemd/system/ledmatrix-wifi-monitor.service")
        if svc_file.exists():
            res = subprocess.run(
                ["systemctl", "is-active", "ledmatrix-wifi-monitor"],
                capture_output=True, text=True,
            )
            status = res.stdout.strip()
            if status == "active":
                r.ok("ledmatrix-wifi-monitor.service", "active")
            else:
                r.warn("ledmatrix-wifi-monitor.service", f"status: {status}")
        else:
            r.warn("ledmatrix-wifi-monitor.service", "Not installed")
    else:
        r.warn("WiFi diagnostics", "Skipped (not a Raspberry Pi)")

    r.render("Network Diagnostics")


# -- diagnose plugins -------------------------------------------------------

@diagnose.command("plugins")
def diagnose_plugins() -> None:
    """Check plugin health: permissions, deps markers, manifests."""
    console.print(Rule("[green]diagnose plugins[/green]"))
    r = _DiagResult()

    # 1. Plugin directory existence & permissions
    if PLUGINS_DIR.exists():
        r.ok("plugins/ directory", str(PLUGINS_DIR))
        if os.access(PLUGINS_DIR, os.R_OK):
            r.ok("plugins/ readable")
        else:
            r.fail("plugins/ readable", "No read permission")
        if os.access(PLUGINS_DIR, os.W_OK):
            r.ok("plugins/ writable")
        else:
            r.warn("plugins/ writable", "No write permission (plugin install may fail)")
    else:
        r.fail("plugins/ directory", f"Not found at {PLUGINS_DIR}")
        r.render("Plugin Diagnostics")
        return

    # 2. plugin-repos directory
    plugin_repos_dir = LEDMATRIX_ROOT / "plugin-repos"
    if plugin_repos_dir.exists():
        r.ok("plugin-repos/ directory", str(plugin_repos_dir))
    else:
        r.warn("plugin-repos/ directory", "Not found (OK if not doing plugin development)")

    # 3. Scan each plugin
    plugin_dirs = sorted(
        p for p in PLUGINS_DIR.iterdir()
        if p.is_dir() or p.is_symlink()
    )

    if not plugin_dirs:
        r.warn("Installed plugins", "No plugins found in plugins/")
        r.render("Plugin Diagnostics")
        return

    for pdir in plugin_dirs:
        pid = pdir.name

        # 3a. Manifest
        manifest = _read_manifest(pdir)
        if manifest is None:
            r.fail(f"[{pid}] manifest.json", "Missing or invalid JSON")
            continue

        # Validate required manifest fields
        required_fields = ["id", "name", "version"]
        missing = [f for f in required_fields if f not in manifest]
        if missing:
            r.warn(f"[{pid}] manifest.json", f"Missing fields: {', '.join(missing)}")
        else:
            r.ok(f"[{pid}] manifest.json", f"v{manifest.get('version', '?')}")

        # 3b. config_schema.json
        schema_file = pdir / "config_schema.json"
        if schema_file.exists():
            try:
                json.loads(schema_file.read_text())
                r.ok(f"[{pid}] config_schema.json")
            except json.JSONDecodeError:
                r.fail(f"[{pid}] config_schema.json", "Invalid JSON")
        else:
            r.warn(f"[{pid}] config_schema.json", "Missing")

        # 3c. manager.py (entry point)
        manager_file = pdir / "manager.py"
        if manager_file.exists():
            r.ok(f"[{pid}] manager.py")
        else:
            r.fail(f"[{pid}] manager.py", "Missing entry point")

        # 3d. Dependencies installed marker
        deps_marker = pdir / ".dependencies_installed"
        if deps_marker.exists():
            r.ok(f"[{pid}] dependencies installed")
        else:
            req_file = pdir / "requirements.txt"
            if req_file.exists() and req_file.read_text().strip():
                r.warn(f"[{pid}] dependencies installed", "Marker missing — run: matrix plugin install")
            else:
                r.ok(f"[{pid}] dependencies", "No requirements")

        # 3e. Directory permissions
        if not os.access(pdir, os.R_OK):
            r.fail(f"[{pid}] permissions", "Not readable")

    r.render("Plugin Diagnostics")


# ---------------------------------------------------------------------------
# fix — permission repair commands
# ---------------------------------------------------------------------------

ASSETS_DIR = LEDMATRIX_ROOT / "assets"
CACHE_DIRS = [
    Path("/var/cache/ledmatrix"),
    Path.home() / ".ledmatrix_cache",
    Path.home() / ".cache" / "ledmatrix",
]
PLUGIN_REPOS_DIR = LEDMATRIX_ROOT / "plugin-repos"
WEB_DIR = LEDMATRIX_ROOT / "web_interface"


def _fix_dir_permissions(target: Path, dir_mode: int, file_mode: int, label: str) -> int:
    """Recursively set *dir_mode* on directories and *file_mode* on files under *target*.

    Returns the number of items whose permissions were changed.
    """
    changed = 0
    if not target.exists():
        console.print(f"  [yellow]Skipped[/yellow] {target} (does not exist)")
        return changed

    for item in target.rglob("*"):
        try:
            current = item.stat().st_mode & 0o7777
            if item.is_dir():
                if current != dir_mode:
                    os.chmod(item, dir_mode)
                    changed += 1
            elif item.is_file():
                if current != file_mode:
                    os.chmod(item, file_mode)
                    changed += 1
        except OSError as exc:
            console.print(f"  [red]Error[/red] {item}: {exc}")

    # Also fix the root directory itself
    try:
        current = target.stat().st_mode & 0o7777
        if current != dir_mode:
            os.chmod(target, dir_mode)
            changed += 1
    except OSError as exc:
        console.print(f"  [red]Error[/red] {target}: {exc}")

    console.print(f"  [green]✓[/green] {label}: {changed} item(s) updated")
    return changed


def _fix_assets_permissions() -> int:
    """Fix assets/ directory permissions (755 dirs, 644 files)."""
    return _fix_dir_permissions(ASSETS_DIR, 0o755, 0o644, "assets/")


def _fix_cache_permissions() -> int:
    """Fix cache directory permissions (775 dirs, 664 files)."""
    changed = 0
    for cache_dir in CACHE_DIRS:
        if cache_dir.exists():
            changed += _fix_dir_permissions(cache_dir, 0o775, 0o664, str(cache_dir))
    if changed == 0:
        console.print("  [dim]No cache directories found[/dim]")
    return changed


def _fix_plugin_permissions() -> int:
    """Fix plugins/ and plugin-repos/ permissions (755 dirs, 644 files)."""
    changed = 0
    for target, label in [(PLUGINS_DIR, "plugins/"), (PLUGIN_REPOS_DIR, "plugin-repos/")]:
        changed += _fix_dir_permissions(target, 0o755, 0o644, label)
    return changed


def _fix_web_permissions() -> int:
    """Fix web_interface/ permissions (755 dirs, 644 files)."""
    return _fix_dir_permissions(WEB_DIR, 0o755, 0o644, "web_interface/")


@cli.group()
def fix():
    """Fix permissions and common issues."""
    pass


@fix.command()
@click.option("--assets", is_flag=True, help="Fix assets/ permissions")
@click.option("--cache", is_flag=True, help="Fix cache/ permissions")
@click.option("--plugins", is_flag=True, help="Fix plugins/ permissions")
@click.option("--web", is_flag=True, help="Fix web_interface/ permissions")
def permissions(assets, cache, plugins, web):
    """Fix file and directory permissions."""
    run_all = not any([assets, cache, plugins, web])

    console.print(Rule("[bold]Fix Permissions[/bold]"))

    total = 0
    if run_all or assets:
        total += _fix_assets_permissions()
    if run_all or cache:
        total += _fix_cache_permissions()
    if run_all or plugins:
        total += _fix_plugin_permissions()
    if run_all or web:
        total += _fix_web_permissions()

    console.print()
    if total:
        console.print(f"[green]Done.[/green] {total} permission(s) updated.")
    else:
        console.print("[green]Done.[/green] All permissions already correct.")


# ---------------------------------------------------------------------------
# clean — housekeeping commands
# ---------------------------------------------------------------------------

@cli.group()
def clean():
    """Remove caches, markers, and backup files."""
    pass


@clean.command()
def cache():
    """Delete __pycache__ dirs, .pyc files, and Flask .webassets-cache."""
    console.print(Rule("[bold]Clean Python Cache[/bold]"))

    removed_dirs = 0
    removed_files = 0

    # Remove __pycache__ directories
    for pycache in list(LEDMATRIX_ROOT.rglob("__pycache__")):
        try:
            shutil.rmtree(pycache)
            removed_dirs += 1
        except OSError as exc:
            console.print(f"  [red]Error[/red] {pycache}: {exc}")

    # Remove .pyc files
    for pyc in list(LEDMATRIX_ROOT.rglob("*.pyc")):
        try:
            pyc.unlink()
            removed_files += 1
        except OSError as exc:
            console.print(f"  [red]Error[/red] {pyc}: {exc}")

    # Remove Flask webassets cache
    webassets = LEDMATRIX_ROOT / "web_interface" / ".webassets-cache"
    if webassets.exists():
        try:
            shutil.rmtree(webassets)
            removed_dirs += 1
        except OSError as exc:
            console.print(f"  [red]Error[/red] {webassets}: {exc}")

    console.print(f"  [green]✓[/green] Removed {removed_dirs} cache dir(s) and {removed_files} .pyc file(s)")


@clean.command()
def deps():
    """Remove .dependencies_installed marker files from plugins."""
    console.print(Rule("[bold]Clean Dependency Markers[/bold]"))

    removed = 0
    search_dirs = [
        Path("/var/cache/ledmatrix"),
        Path.home() / ".cache" / "ledmatrix",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for marker in list(search_dir.glob("plugin_*_deps_installed")):
            try:
                marker.unlink()
                removed += 1
            except OSError as exc:
                console.print(f"  [red]Error[/red] {marker}: {exc}")

    # Also check inside plugin directories
    if PLUGINS_DIR.exists():
        for marker in list(PLUGINS_DIR.rglob(".dependencies_installed")):
            try:
                marker.unlink()
                removed += 1
            except OSError as exc:
                console.print(f"  [red]Error[/red] {marker}: {exc}")

    console.print(f"  [green]✓[/green] Removed {removed} dependency marker(s)")


@clean.command()
def backups():
    """Remove *_backup dirs and *.bak files from plugins/."""
    console.print(Rule("[bold]Clean Plugin Backups[/bold]"))

    removed = 0

    if not PLUGINS_DIR.exists():
        console.print("  [yellow]Skipped[/yellow] plugins/ does not exist")
        return

    # Remove *_backup and *.backup* directories
    for pattern in ["*_backup", "*.backup*"]:
        for backup in list(PLUGINS_DIR.glob(pattern)):
            if backup.is_dir():
                try:
                    shutil.rmtree(backup)
                    removed += 1
                    console.print(f"  Removed dir  {backup.name}")
                except OSError as exc:
                    console.print(f"  [red]Error[/red] {backup}: {exc}")

    # Remove *.bak files
    for bak in list(PLUGINS_DIR.rglob("*.bak")):
        try:
            bak.unlink()
            removed += 1
            console.print(f"  Removed file {bak.name}")
        except OSError as exc:
            console.print(f"  [red]Error[/red] {bak}: {exc}")

    console.print(f"  [green]✓[/green] Removed {removed} backup item(s)")


# ---------------------------------------------------------------------------
# matrix network
# ---------------------------------------------------------------------------

CAPTIVE_PORTAL_URL = "http://detectportal.firefox.com/canonical.html"


@cli.group()
@click.pass_context
def network(ctx: click.Context) -> None:
    """Network and WiFi management."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _check_ping(host: str = "8.8.8.8", timeout: int = 3) -> bool:
    """Return True if host responds to a single ICMP ping."""
    flag = "-W" if platform.system() != "Windows" else "-w"
    timeout_val = str(timeout) if platform.system() != "Windows" else str(timeout * 1000)
    result = subprocess.run(
        ["ping", "-c", "1", flag, timeout_val, host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _get_ip_address() -> str:
    """Return the primary IP address or 'N/A'."""
    try:
        output = subprocess.check_output(["hostname", "-I"], stderr=subprocess.DEVNULL)
        ips = output.decode().strip().split()
        return ips[0] if ips else "N/A"
    except Exception:
        return "N/A"


def _check_dns(hostname: str = "google.com") -> bool:
    """Return True if hostname resolves via DNS."""
    try:
        socket.getaddrinfo(hostname, 443)
        return True
    except OSError:
        return False


def _get_wifi_info() -> dict:
    """Parse iwconfig wlan0 output for WiFi info (Pi only)."""
    info: dict = {"ssid": "N/A", "signal": "N/A", "quality": "N/A"}
    try:
        output = subprocess.check_output(
            ["iwconfig", "wlan0"], stderr=subprocess.DEVNULL
        ).decode()
        if 'ESSID:"' in output:
            start = output.index('ESSID:"') + 7
            end = output.index('"', start)
            info["ssid"] = output[start:end]
        if "Signal level=" in output:
            start = output.index("Signal level=") + 13
            end = output.index(" ", start)
            info["signal"] = output[start:end]
        if "Link Quality=" in output:
            start = output.index("Link Quality=") + 13
            end = output.index(" ", start)
            info["quality"] = output[start:end]
    except Exception:
        pass
    return info


@network.command()
def status() -> None:
    """Show network connectivity, IP address, DNS, and WiFi signal."""
    t = Table(title="Network Status", show_header=True, header_style="bold green", border_style="dim")
    t.add_column("Check", min_width=20)
    t.add_column("Result", min_width=30)

    is_online = _check_ping()
    t.add_row(
        "Internet",
        Text("Online", style="bold green") if is_online else Text("Offline", style="bold red"),
    )

    ip_addr = _get_ip_address()
    t.add_row("IP Address", ip_addr)

    dns_ok = _check_dns()
    t.add_row(
        "DNS Resolution",
        Text("OK", style="green") if dns_ok else Text("Failed", style="red"),
    )

    if _is_raspberry_pi():
        wifi = _get_wifi_info()
        t.add_row("WiFi SSID", wifi["ssid"])
        t.add_row("WiFi Signal", wifi["signal"])
        t.add_row("WiFi Quality", wifi["quality"])

    console.print(t)


@network.command()
def reconnect() -> None:
    """Attempt to restore network connectivity (Pi only, requires sudo)."""
    if not _is_raspberry_pi():
        console.print(
            Panel(
                "[yellow]This command is only available on Raspberry Pi.[/yellow]\n\n"
                "Use [bold]matrix network status[/bold] to check connectivity on any platform.",
                title="[dim]Not a Raspberry Pi[/dim]",
                border_style="yellow",
            )
        )
        return

    if os.geteuid() != 0:
        console.print(
            Panel(
                "[yellow]This command requires root privileges.[/yellow]\n\n"
                "Run with sudo:\n"
                "  [bold green]sudo matrix network reconnect[/bold green]",
                title="[red]Sudo Required[/red]",
                border_style="red",
            )
        )
        return

    console.print(Rule("[bold]Network Reconnect[/bold]"))
    console.print("\n[bold]Step 1:[/bold] Checking current connectivity...")

    if _check_ping():
        console.print("  [green]Already connected to the internet.[/green]")
        return

    console.print("  [red]No internet connectivity detected.[/red]\n")

    console.print("[bold]Step 2:[/bold] Restarting network service...")
    for svc in ("NetworkManager", "networking"):
        result = subprocess.run(
            ["systemctl", "restart", svc],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            console.print(f"  [green]Restarted {svc}[/green]")
            break
    else:
        console.print("  [yellow]Could not restart network service[/yellow]")

    console.print("\n[bold]Step 3:[/bold] Waiting for connectivity (up to 30s)...")
    connected = False
    for i in range(6):
        time.sleep(5)
        if _check_ping():
            connected = True
            break
        console.print(f"  [dim]...{(i + 1) * 5}s[/dim]")

    if connected:
        console.print("  [bold green]Internet connectivity restored![/bold green]")
        return

    console.print("  [red]Still no connectivity after NetworkManager restart.[/red]\n")

    console.print("[bold]Step 4:[/bold] Trying DHCP release/renew...")
    subprocess.run(["dhclient", "-r", "wlan0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.run(["dhclient", "wlan0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    if _check_ping():
        console.print("  [bold green]Internet connectivity restored after DHCP renew![/bold green]")
    else:
        console.print(
            Panel(
                "[red]Could not restore connectivity.[/red]\n\n"
                "Manual troubleshooting:\n"
                "  1. Check WiFi: [bold]nmcli device status[/bold]\n"
                "  2. Scan networks: [bold]nmcli device wifi list[/bold]\n"
                "  3. Reconnect: [bold]nmcli device wifi connect <SSID> password <pass>[/bold]\n"
                "  4. Check routes: [bold]ip route show[/bold]",
                title="[red]Reconnect Failed[/red]",
                border_style="red",
            )
        )


@network.command("test-portal")
def test_portal() -> None:
    """Check for captive portal by probing a detection endpoint."""
    console.print(Rule("[bold]Captive Portal Test[/bold]"))
    console.print(f"\n  Probing [cyan]{CAPTIVE_PORTAL_URL}[/cyan] ...\n")

    try:
        resp = requests.get(CAPTIVE_PORTAL_URL, timeout=5, allow_redirects=True)
    except Exception:
        console.print(
            Panel(
                "[red]Could not reach the detection endpoint.[/red]\n\n"
                "This usually means there is no network connectivity.\n"
                "Run [bold]matrix network status[/bold] to diagnose.",
                title="[red]No Connectivity[/red]",
                border_style="red",
            )
        )
        return

    if "success" in resp.text.lower():
        console.print(
            Panel(
                "[bold green]No captive portal detected.[/bold green]\n\n"
                "Your connection to the internet is direct and unrestricted.",
                title="[green]All Clear[/green]",
                border_style="green",
            )
        )
    else:
        portal_url = resp.url if resp.url != CAPTIVE_PORTAL_URL else "unknown"
        console.print(
            Panel(
                "[bold yellow]Captive portal detected![/bold yellow]\n\n"
                f"You were redirected to:\n  [cyan]{portal_url}[/cyan]\n\n"
                "Open the URL above in a browser to authenticate.",
                title="[yellow]Captive Portal[/yellow]",
                border_style="yellow",
            )
        )


# ---------------------------------------------------------------------------
# matrix uninstall
# ---------------------------------------------------------------------------

_SYSTEMD_DIR = Path("/etc/systemd/system")
_SUDOERS_DIR = Path("/etc/sudoers.d")
_MATRIX_SYMLINK = Path("/usr/local/bin/matrix")

_SERVICE_UNITS = ["ledmatrix.service", "ledmatrix-web.service"]
_SERVICE_NAMES = ["ledmatrix", "ledmatrix-web"]


def _sudo_run(cmd: list, *, check: bool = False) -> int:
    """Run a command with sudo, returning the exit code."""
    return subprocess.run(["sudo"] + cmd, check=check).returncode


def _uninstall_step_stop_services() -> None:
    for svc in _SERVICE_NAMES:
        rc = _sudo_run(["systemctl", "stop", svc])
        if rc == 0:
            console.print(f"  [green]✓[/green] Stopped {svc}")
        else:
            console.print(f"  [dim]- Skipped stopping {svc} (not running)[/dim]")


def _uninstall_step_disable_services() -> None:
    for svc in _SERVICE_NAMES:
        rc = _sudo_run(["systemctl", "disable", svc])
        if rc == 0:
            console.print(f"  [green]✓[/green] Disabled {svc}")
        else:
            console.print(f"  [dim]- Skipped disabling {svc} (not enabled)[/dim]")


def _uninstall_step_remove_unit_files() -> None:
    removed_any = False
    for unit in _SERVICE_UNITS:
        unit_path = _SYSTEMD_DIR / unit
        if unit_path.exists():
            _sudo_run(["rm", "-f", str(unit_path)])
            console.print(f"  [green]✓[/green] Removed {unit_path}")
            removed_any = True
        else:
            console.print(f"  [dim]- Skipped {unit_path} (not found)[/dim]")
    if removed_any:
        _sudo_run(["systemctl", "daemon-reload"])
        console.print("  [green]✓[/green] Reloaded systemd daemon")


def _uninstall_step_remove_sudoers() -> None:
    if _SUDOERS_DIR.exists():
        found = list(_SUDOERS_DIR.glob("ledmatrix-*"))
        if found:
            for f in found:
                _sudo_run(["rm", "-f", str(f)])
                console.print(f"  [green]✓[/green] Removed {f}")
        else:
            console.print("  [dim]- Skipped sudoers (no ledmatrix-* files found)[/dim]")
    else:
        console.print("  [dim]- Skipped sudoers (/etc/sudoers.d not found)[/dim]")


def _uninstall_step_remove_symlink() -> None:
    if _MATRIX_SYMLINK.exists() or _MATRIX_SYMLINK.is_symlink():
        _sudo_run(["rm", "-f", str(_MATRIX_SYMLINK)])
        console.print(f"  [green]✓[/green] Removed {_MATRIX_SYMLINK}")
    else:
        console.print(f"  [dim]- Skipped {_MATRIX_SYMLINK} (not found)[/dim]")


def _uninstall_step_remove_data(*, keep_config: bool, keep_plugins: bool, keep_venv: bool) -> None:
    config_json = LEDMATRIX_ROOT / "config" / "config.json"
    config_secrets = LEDMATRIX_ROOT / "config" / "config_secrets.json"
    if keep_config:
        console.print("  [yellow]⚠[/yellow] Kept config files (--keep-config)")
    else:
        for cfg in (config_json, config_secrets):
            if cfg.exists():
                cfg.unlink()
                console.print(f"  [green]✓[/green] Removed {cfg.relative_to(LEDMATRIX_ROOT)}")
            else:
                console.print(f"  [dim]- Skipped {cfg.relative_to(LEDMATRIX_ROOT)} (not found)[/dim]")

    plugins_dir = LEDMATRIX_ROOT / "plugins"
    if keep_plugins:
        console.print("  [yellow]⚠[/yellow] Kept plugins (--keep-plugins)")
    else:
        if plugins_dir.exists() and any(plugins_dir.iterdir()):
            for item in plugins_dir.iterdir():
                if item.is_dir() and not item.is_symlink():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            console.print("  [green]✓[/green] Removed plugins/ contents")
        else:
            console.print("  [dim]- Skipped plugins/ (empty or not found)[/dim]")

    venv_dir = LEDMATRIX_ROOT / ".venv"
    if keep_venv:
        console.print("  [yellow]⚠[/yellow] Kept .venv (--keep-venv)")
    else:
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
            console.print("  [green]✓[/green] Removed .venv/")
        else:
            console.print("  [dim]- Skipped .venv/ (not found)[/dim]")


def _uninstall_step_remove_group() -> None:
    rc = _sudo_run(["groupdel", "ledmatrix"])
    if rc == 0:
        console.print("  [green]✓[/green] Removed ledmatrix group")
    else:
        console.print("  [dim]- Skipped ledmatrix group (not found or not empty)[/dim]")


@cli.command()
@click.option("--keep-config", is_flag=True, help="Preserve config/config.json and config_secrets.json")
@click.option("--keep-plugins", is_flag=True, help="Preserve installed plugins")
@click.option("--keep-venv", is_flag=True, help="Preserve .venv directory")
@click.option("--all", "remove_all", is_flag=True, help="Remove everything including config and plugins")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def uninstall(keep_config: bool, keep_plugins: bool, keep_venv: bool,
              remove_all: bool, yes: bool) -> None:
    """Uninstall LEDMatrix services and optionally remove data."""
    console.print(Rule("[red]uninstall[/red]"))

    if remove_all:
        keep_config = False
        keep_plugins = False
        keep_venv = False

    console.print("\n  [bold]The following will be removed:[/bold]")
    console.print("    • systemd services (ledmatrix, ledmatrix-web)")
    console.print("    • systemd unit files")
    console.print("    • sudoers rules (/etc/sudoers.d/ledmatrix-*)")
    console.print("    • /usr/local/bin/matrix symlink")
    if not keep_config:
        console.print("    • config/config.json and config_secrets.json")
    if not keep_plugins:
        console.print("    • plugins/ directory contents")
    if not keep_venv:
        console.print("    • .venv/ directory")
    console.print("    • ledmatrix system group\n")

    if keep_config:
        console.print("  [yellow]⚠[/yellow] Config files will be preserved (--keep-config)")
    if keep_plugins:
        console.print("  [yellow]⚠[/yellow] Plugins will be preserved (--keep-plugins)")
    if keep_venv:
        console.print("  [yellow]⚠[/yellow] .venv will be preserved (--keep-venv)")

    if not yes:
        console.print()
        if not click.confirm("  Are you sure?", default=False):
            console.print("  [dim]Uninstall cancelled.[/dim]")
            return

    console.print()

    console.print("  [bold]Step 1/8: Stopping services[/bold]")
    _uninstall_step_stop_services()

    console.print("  [bold]Step 2/8: Disabling services[/bold]")
    _uninstall_step_disable_services()

    console.print("  [bold]Step 3/8: Removing unit files[/bold]")
    _uninstall_step_remove_unit_files()

    console.print("  [bold]Step 4/8: Removing sudoers rules[/bold]")
    _uninstall_step_remove_sudoers()

    console.print("  [bold]Step 5/8: Removing matrix symlink[/bold]")
    _uninstall_step_remove_symlink()

    console.print("  [bold]Step 6/8: Removing data[/bold]")
    _uninstall_step_remove_data(
        keep_config=keep_config,
        keep_plugins=keep_plugins,
        keep_venv=keep_venv,
    )

    console.print("  [bold]Step 7/8: Removing ledmatrix group[/bold]")
    _uninstall_step_remove_group()

    console.print("  [bold]Step 8/8: Cleanup complete[/bold]")
    console.print(Panel(
        "[green]LEDMatrix has been uninstalled.[/green]\n\n"
        "The source code remains in this directory.\n"
        "To reinstall, run: [bold]matrix install[/bold]",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
