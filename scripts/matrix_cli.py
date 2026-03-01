#!/usr/bin/env python3
"""
matrix — LEDMatrix developer CLI.

"You take the red pill, you stay in Wonderland,
 and I show you how deep the rabbit hole goes."
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Resolve the LEDMatrix project root relative to this script's real location,
# so the /usr/local/bin/matrix symlink works correctly from any directory.
LEDMATRIX_ROOT = Path(__file__).resolve().parent.parent

# Prefer the project venv so all LEDMatrix dependencies (PIL, rgbmatrix, etc.)
# are available. Fall back to the current interpreter if the venv isn't present.
_venv_python = LEDMATRIX_ROOT / ".venv" / "bin" / "python3"
PYTHON = str(_venv_python) if _venv_python.exists() else sys.executable

# ANSI
GREEN  = "\033[32m"
DIM    = "\033[2m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = f"""{GREEN}
  ░▒▓ MATRIX ▓▒░  LED edition
  {"─" * 36}
  {DIM}"There is no spoon. There is only the display."{RESET}{GREEN}
{RESET}"""

BANNER_PLAIN = """
  ░▒▓ MATRIX ▓▒░  LED edition
  ────────────────────────────────────
  "There is no spoon. There is only the display."
"""


def print_banner() -> None:
    if sys.stdout.isatty():
        print(BANNER)
    else:
        print(BANNER_PLAIN)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list, **kwargs) -> int:
    """Run a command and return its exit code."""
    return subprocess.run(cmd, **kwargs).returncode


def die(msg: str, code: int = 1) -> None:
    print(f"  [error] {msg}", file=sys.stderr)
    sys.exit(code)


def ok(msg: str) -> None:
    prefix = f"{GREEN}  >{RESET}" if sys.stdout.isatty() else "  >"
    print(f"{prefix} {msg}")


def info(msg: str) -> None:
    prefix = f"{DIM}  ·{RESET}" if sys.stdout.isatty() else "  ·"
    print(f"{prefix} {msg}")


# ---------------------------------------------------------------------------
# matrix run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    """Start the LED display in emulator mode."""
    print_banner()
    ok("Starting display — emulator mode.")
    info(f"root: {LEDMATRIX_ROOT}")
    env = {**os.environ, "EMULATOR": "true"}
    return run([PYTHON, str(LEDMATRIX_ROOT / "run.py")], env=env)


# ---------------------------------------------------------------------------
# matrix web
# ---------------------------------------------------------------------------

def cmd_web(args: argparse.Namespace) -> int:
    """Start the web interface."""
    print_banner()
    ok("Starting web interface on http://localhost:5000")
    return run([PYTHON, str(LEDMATRIX_ROOT / "web_interface" / "start.py")])


# ---------------------------------------------------------------------------
# matrix plugin new
# ---------------------------------------------------------------------------

MANIFEST_TEMPLATE = {
    "id": "{id}",
    "name": "{name}",
    "version": "0.1.0",
    "author": "",
    "description": "",
    "entry_point": "manager.py",
    "class_name": "{class_name}",
    "category": "other",
    "tags": [],
    "display_modes": ["{id}"],
    "update_interval": 60,
    "default_duration": 15,
}

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
        "type": {{
          "type": "string",
          "enum": ["redraw", "fade", "slide", "wipe"],
          "default": "redraw"
        }},
        "speed": {{
          "type": "integer",
          "default": 2,
          "minimum": 1,
          "maximum": 10
        }},
        "enabled": {{
          "type": "boolean",
          "default": true
        }}
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
        """Fetch or prepare data for display."""
        self.logger.debug("{id}: update() called")

    def display(self, force_clear: bool = False) -> None:
        """Render content to the LED matrix."""
        self.logger.debug("{id}: display() called — %dx%d",
                          self.display_manager.width, self.display_manager.height)
        self.display_manager.clear()

    def validate_config(self) -> bool:
        return super().validate_config()

    def on_config_change(self, new_config: Dict[str, Any]) -> None:
        super().on_config_change(new_config)
'''

GITIGNORE_CONTENT = """\
__pycache__/
*.py[cod]
*.egg-info/
.dependencies_installed
.env
"""

REQUIREMENTS_CONTENT = """\
# Add your plugin dependencies here, e.g.:
# requests>=2.28.0
"""


def _to_class_name(plugin_id: str) -> str:
    """transit-board -> TransitBoardPlugin"""
    return "".join(part.capitalize() for part in plugin_id.replace("_", "-").split("-")) + "Plugin"


def _to_display_name(plugin_id: str) -> str:
    """transit-board -> Transit Board"""
    return " ".join(part.capitalize() for part in plugin_id.replace("_", "-").split("-"))


def cmd_plugin_new(args: argparse.Namespace) -> int:
    """Scaffold a new plugin directory with all required files."""
    print_banner()

    plugin_id = args.id
    base_path = Path(args.path).resolve() if args.path else Path.cwd()
    plugin_dir = base_path / plugin_id

    class_name = _to_class_name(plugin_id)
    display_name = _to_display_name(plugin_id)

    if plugin_dir.exists():
        die(f"Directory already exists: {plugin_dir}")

    ok(f"Scaffolding plugin '{plugin_id}' at {plugin_dir}")
    plugin_dir.mkdir(parents=True)

    # manifest.json
    manifest = {k: v.format(id=plugin_id, name=display_name, class_name=class_name)
                if isinstance(v, str) else v
                for k, v in MANIFEST_TEMPLATE.items()}
    manifest["id"] = plugin_id
    manifest["display_modes"] = [plugin_id]
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    info("manifest.json")

    # config_schema.json
    (plugin_dir / "config_schema.json").write_text(
        SCHEMA_TEMPLATE.format(name=display_name)
    )
    info("config_schema.json")

    # manager.py
    (plugin_dir / "manager.py").write_text(
        MANAGER_TEMPLATE.format(id=plugin_id, name=display_name, class_name=class_name)
    )
    info("manager.py")

    # requirements.txt
    (plugin_dir / "requirements.txt").write_text(REQUIREMENTS_CONTENT)
    info("requirements.txt")

    # .gitignore
    (plugin_dir / ".gitignore").write_text(GITIGNORE_CONTENT)
    info(".gitignore")

    # git init
    run(["git", "init", "-b", "main", str(plugin_dir)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    info("git init (branch: main)")

    # pre-push versioning hook
    hook_src = LEDMATRIX_ROOT / "scripts" / "git-hooks" / "pre-push-plugin-version"
    hooks_dir = plugin_dir / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    if hook_src.exists():
        shutil.copy(hook_src, hooks_dir / "pre-push")
        (hooks_dir / "pre-push").chmod(0o755)
        info(".git/hooks/pre-push (auto-version bump on push)")
    else:
        info(f".git/hooks/pre-push — hook source not found at {hook_src}, skipping")

    print()
    ok(f"Plugin '{plugin_id}' created.")
    print(f"\n  Next steps:\n")
    print(f"    matrix plugin link {plugin_id} {plugin_dir}")
    print(f"    matrix plugin render {plugin_id}")
    print()
    return 0


# ---------------------------------------------------------------------------
# matrix plugin link / unlink / list / status
# ---------------------------------------------------------------------------

DEV_SETUP = LEDMATRIX_ROOT / "scripts" / "dev" / "dev_plugin_setup.sh"


def _dev_setup(*args_) -> int:
    if not DEV_SETUP.exists():
        die(f"dev_plugin_setup.sh not found at {DEV_SETUP}")
    return run(["bash", str(DEV_SETUP), *args_], cwd=str(LEDMATRIX_ROOT))


def cmd_plugin_link(args: argparse.Namespace) -> int:
    print_banner()
    ok(f"Linking '{args.id}' from {args.path}")
    return _dev_setup("link", args.id, args.path)


def cmd_plugin_unlink(args: argparse.Namespace) -> int:
    print_banner()
    ok(f"Unlinking '{args.id}'")
    return _dev_setup("unlink", args.id)


def cmd_plugin_list(args: argparse.Namespace) -> int:
    print_banner()
    return _dev_setup("list")


def cmd_plugin_status(args: argparse.Namespace) -> int:
    print_banner()
    return _dev_setup("status")


# ---------------------------------------------------------------------------
# matrix plugin render
# ---------------------------------------------------------------------------

def cmd_plugin_render(args: argparse.Namespace) -> int:
    """Render a plugin to PNG without running the full display loop."""
    print_banner()
    render_script = LEDMATRIX_ROOT / "scripts" / "render_plugin.py"
    if not render_script.exists():
        die(f"render_plugin.py not found at {render_script}")

    cmd = [PYTHON, str(render_script), "--plugin", args.id]
    if args.output:
        cmd += ["--output", args.output]
    if args.width:
        cmd += ["--width", str(args.width)]
    if args.height:
        cmd += ["--height", str(args.height)]

    ok(f"Rendering plugin '{args.id}'")
    return run(cmd, cwd=str(LEDMATRIX_ROOT))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matrix",
        description="LEDMatrix developer CLI — LED edition.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='  "Wake up, Neo." — run `matrix run` to find out how deep it goes.',
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # matrix run
    p_run = sub.add_parser("run", help="Start the display in emulator mode")
    p_run.set_defaults(func=cmd_run)

    # matrix web
    p_web = sub.add_parser("web", help="Start the web interface (localhost:5000)")
    p_web.set_defaults(func=cmd_web)

    # matrix plugin <subcommand>
    p_plugin = sub.add_parser("plugin", help="Plugin management commands")
    plugin_sub = p_plugin.add_subparsers(dest="plugin_command", metavar="<subcommand>")

    # matrix plugin new
    p_new = plugin_sub.add_parser("new", help="Scaffold a new plugin")
    p_new.add_argument("id", help="Plugin ID (e.g. transit-board)")
    p_new.add_argument("path", nargs="?", default=None,
                       help="Directory to create plugin in (default: current directory)")
    p_new.set_defaults(func=cmd_plugin_new)

    # matrix plugin link
    p_link = plugin_sub.add_parser("link", help="Link a plugin repo into the display runtime")
    p_link.add_argument("id", help="Plugin ID")
    p_link.add_argument("path", help="Path to the plugin repo")
    p_link.set_defaults(func=cmd_plugin_link)

    # matrix plugin unlink
    p_unlink = plugin_sub.add_parser("unlink", help="Remove a plugin symlink")
    p_unlink.add_argument("id", help="Plugin ID")
    p_unlink.set_defaults(func=cmd_plugin_unlink)

    # matrix plugin list
    p_list = plugin_sub.add_parser("list", help="List all plugins and their link status")
    p_list.set_defaults(func=cmd_plugin_list)

    # matrix plugin status
    p_status = plugin_sub.add_parser("status", help="Show git status of all linked plugin repos")
    p_status.set_defaults(func=cmd_plugin_status)

    # matrix help
    sub.add_parser("help", help="Show this help message")

    # matrix plugin render
    p_render = plugin_sub.add_parser("render", help="Render a plugin to PNG")
    p_render.add_argument("id", help="Plugin ID")
    p_render.add_argument("--output", "-o", default=None,
                          help="Output PNG path (default: /tmp/plugin_render.png)")
    p_render.add_argument("--width", type=int, default=None, help="Display width in pixels")
    p_render.add_argument("--height", type=int, default=None, help="Display height in pixels")
    p_render.set_defaults(func=cmd_plugin_render)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command or args.command == "help":
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "plugin" and not args.plugin_command:
        print_banner()
        parser.parse_args(["plugin", "--help"])
        sys.exit(0)

    if not hasattr(args, "func"):
        print_banner()
        parser.print_help()
        sys.exit(1)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
