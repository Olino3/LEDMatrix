#!/usr/bin/env python3
"""
matrix — LEDMatrix developer CLI.

"You take the red pill, you stay in Wonderland,
 and I show you how deep the rabbit hole goes."
"""

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
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
        console.print("[green]\u2713 .venv is ready[/green]")
    sys.exit(rc)


# ---------------------------------------------------------------------------
# matrix install
# ---------------------------------------------------------------------------

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
        console.print(f"  [dim]No plugins found{f' matching \"{query}\"' if query else ''}.[/dim]")
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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
