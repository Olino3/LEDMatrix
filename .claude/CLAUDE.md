# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

The host machine is Fedora (immutable/Silverblue). System packages like `python3-devel` cannot be installed directly. Until a container-based dev setup is created (Phase 4), **all commands that need build tools or the venv must run inside the Debian Trixie distrobox.**

### Distrobox quirk: venv rebuilds each session

The `.venv` is **ephemeral** — it disappears when the distrobox container restarts because `uv` links to a container-local Python interpreter. Always chain `uv sync` before any venv command:

```bash
# CORRECT — chain uv sync with the command in a single distrobox invocation
distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins'

# WRONG — venv will be gone by the second command
distrobox enter debian-trixie -- uv sync
distrobox enter debian-trixie -- .venv/bin/pytest test/  # ❌ .venv/bin/pytest: No such file
```

The rebuild is fast (~1-2s) because `uv` caches compiled wheels. Always use `--extra test --extra dev --extra emulator` for the full dev environment.

### Distrobox installed packages

The distrobox has these build deps pre-installed:
`python3-dev`, `libffi-dev`, `build-essential`, `libsdl2-dev`, `libsdl2-image-dev`, `libsdl2-mixer-dev`, `libsdl2-ttf-dev`, `libfreetype6-dev`, `pkg-config`

### When to use distrobox

**Need distrobox:** pytest, mypy, `uv sync`, `uv pip install`, running `scripts/matrix_cli.py` with venv deps, any C compilation

**Do NOT need distrobox:** `git`, `gh`, file reads/writes, `grep`, `ls`, basic shell, `python3 -c "import ast; ..."` (syntax checks)

## Commands

### Running the Display
```bash
# On actual Raspberry Pi hardware (requires sudo)
sudo python3 run.py

# In emulator mode for development (no hardware needed)
EMULATOR=true python3 run.py
python3 run.py --emulator      # equivalent CLI flag
python3 run.py --debug         # enable verbose debug logging
# or
bash scripts/dev/run_emulator.sh
```

### Running the Web Interface
```bash
python3 src/api/start.py
# Accessible at http://localhost:5000
```

### Testing a Single Plugin (no full display loop)
```bash
python3 scripts/render_plugin.py <plugin-id>
```

### Running Tests
```bash
# All tests (with coverage) — run inside distrobox
EMULATOR=true .venv/bin/pytest test/ -q

# Single test file
pytest test/test_plugin_system.py -v

# Single test function
pytest test/test_cache_manager.py::TestCacheManager::test_set_and_get -v

# By marker (unit, integration, plugin, hardware, slow)
pytest -m unit
```

### Type Checking
```bash
mypy src/
```

### Matrix CLI (install / remove)
```bash
sudo make install-matrix   # symlink matrix CLI to /usr/local/bin/matrix
sudo make remove-matrix    # remove the symlink
```

## Architecture Overview

### Entry Points
- `run.py` → `src/display_controller.py` — Main display loop
- `src/api/start.py` → `src/api/main.py` — FastAPI web UI (port 5000, uvicorn)

### Core Runtime Flow
`DisplayController` initializes singletons in order: `ConfigManager`/`ConfigService` → `DisplayManager` → `CacheManager` → `FontManager` → `PluginManager`. The display loop cycles through enabled plugins calling `update()` then `display()`.

### Plugin System
Plugins live in `plugins/<plugin-id>/` and inherit from `BasePlugin` (`src/plugin_system/base_plugin.py`). Required files: `manifest.json`, `config_schema.json`, `manager.py`, `requirements.txt`. Required methods: `update()`, `display(force_clear=False)`. See `.claude/rules/plugin-dev.md` for full contract.

**Available BasePlugin properties:** `self.plugin_id`, `self.config`, `self.display_manager`, `self.cache_manager`, `self.plugin_manager`, `self.logger`, `self.enabled`, `self.transition_manager`

**Standard plugin config fields:**
```json
{ "enabled": true, "display_duration": 15, "live_priority": false, "high_performance_transitions": false, "transition": {"type": "redraw", "speed": 2, "enabled": true} }
```

### Web Interface
FastAPI app at `src/api/main.py` with routers in `src/api/routers/` (plugins, config, system, store, fonts, wifi, assets, starlark, streams). SSE streams: `/api/v3/stream/stats`, `/api/v3/stream/display`, `/api/v3/stream/logs`. Static files and HTMX templates remain in `web_interface/static/` and `web_interface/templates/` (pending Phase 3 Angular migration).

### Config System
- `config/config.json` — all user settings (gitignored, created from `config/config.template.json`)
- `config/config_secrets.json` — API keys (gitignored)
- Plugin configs stored under plugin ID inside `config/config.json` — not in plugin directory

### Helper Libraries
- `src/common/` — `scroll_helper.py`, `text_helper.py`, `logo_helper.py`, `display_helper.py`, `api_helper.py`, `game_helper.py`
- `src/base_classes/` — `sports.py`, `hockey.py`, `football.py`, `basketball.py`, `baseball.py`

## Environment Variables
| Variable | Purpose |
|---|---|
| `EMULATOR=true` | Use `RGBMatrixEmulator` instead of real hardware |
| `LEDMATRIX_HOT_RELOAD=true` | Enable config file hot-reload via `ConfigService` |
| `LEDMATRIX_DEBUG=true` | Enable verbose debug logging |
| `LEDMATRIX_JSON_LOGGING=true` | Structured JSON log output (web interface) |

## Common Pitfalls
- `DisplayManager` is a singleton — only one instance exists at runtime
- paho-mqtt 2.x requires `callback_api_version=mqtt.CallbackAPIVersion.VERSION1` for v1 compat
- Use `get_logger()` from `src.logging_config` — NEVER `logging.getLogger()`
- `display_manager.width` / `.height` — NEVER `display_manager.matrix.width` / `.matrix.height`
- When modifying a plugin in the monorepo, bump `version` in `manifest.json` AND run `python update_registry.py`
- `EMULATOR=true` switches the `rgbmatrix` import to `RGBMatrixEmulator` in `src/display_manager.py`
- 7 pre-existing test failures (mock attribute, tkinter, web API 503) are known — do not fix unrelated tests
- Click 8.x: `CliRunner(mix_stderr=False)` is NOT supported — use `CliRunner()` without that parameter
- CLI tests that invoke destructive commands (`uninstall`, `clean`) MUST mock all filesystem operations (`shutil.rmtree`, `Path.unlink`, `subprocess.run`) to prevent damage to the real environment (e.g. deleting `.venv`)
- The default branch is `develop` — worktrees and feature branches MUST branch from `develop`, not `main`

## External Repositories

The user (Olino3) owns these related repos:

| Repo | Local path | Purpose |
|------|-----------|---------|
| `git@github.com:Olino3/ledmatrix-plugins.git` | `~/git/ledmatrix-plugins` | Plugin monorepo (fork of ChuckBuilds/ledmatrix-plugins) |
| `git@github.com:Olino3/ledmatrix-transit-board.git` | `~/git/ledmatrix-transit-board` | Transit board plugin |

**IMPORTANT:** When opening PRs for plugin repos, open them on `Olino3/*` — NOT on `ChuckBuilds/*` (upstream). The user controls their own fork.

## Development Setup for Plugins
```bash
python scripts/setup_plugin_repos.py            # set up all symlinks
./dev_plugin_setup.sh link <name> <path-to-repo> # link a specific repo
```
`plugin-repos/` — development symlinks (tracked); `plugins/` — runtime directory (gitignored).

## Monitoring on Raspberry Pi
```bash
journalctl -u ledmatrix -f        # display service logs
journalctl -u ledmatrix-web -f    # web service logs
```

## Git Conventions
**Branch naming:** `feature/`, `fix/`, `hotfix/`, `refactor/` + kebab-case description

**Commit format:** `type(scope): description`
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Merge strategy:** Squash and merge preferred. `main` is protected — all changes via PR.
