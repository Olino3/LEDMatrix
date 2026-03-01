# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
python3 web_interface/start.py
# Accessible at http://localhost:5000
```

### Testing a Single Plugin (no full display loop)
```bash
python3 scripts/render_plugin.py <plugin-id>
```

### Running Tests
```bash
# All tests (with coverage)
pytest

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

## Architecture Overview

### Entry Points
- `run.py` → `src/display_controller.py` — Main display loop entry point
- `web_interface/start.py` → `web_interface/app.py` — Flask web UI (port 5000)

### Core Runtime Flow
`DisplayController` initializes these singletons in order:
1. `ConfigManager` / `ConfigService` — loads `config/config.json` with optional hot-reload
2. `DisplayManager` — singleton that wraps `rgbmatrix` (or `RGBMatrixEmulator` when `EMULATOR=true`)
3. `CacheManager` — shared cache for API responses
4. `FontManager` — freetype font loading
5. `PluginManager` — discovers and loads plugins from `plugins/`

The display loop cycles through enabled plugins, calling `update()` then `display()` on each.

### Plugin System
Plugins live in `plugins/<plugin-id>/` and inherit from `BasePlugin` (`src/plugin_system/base_plugin.py`).

**Required files per plugin:**
- `manifest.json` — id, name, version, description, entry_point, class_name, display_modes
- `config_schema.json` — JSON Schema Draft-7 for plugin config
- `manager.py` — contains the class inheriting `BasePlugin`
- `requirements.txt`

**Required abstract methods:**
- `update()` — fetch data, called on the plugin's update interval
- `display(force_clear=False)` — render to the LED matrix

**Important optional lifecycle hooks:**
- `validate_config()` — validate config at load time
- `on_config_change()` — called when config is updated via the web API
- `on_enable()` / `on_disable()` — called when plugin is toggled
- `cleanup()` — release resources on unload

**Live priority hooks** (plugin pre-empts others when live content is present):
- `has_live_priority()` — returns True if live priority is enabled in config
- `has_live_content()` — return True when live/urgent content is available
- `get_live_modes()` — list of display modes active during live takeover

**Dynamic duration hooks** (plugin controls its own display time):
- `supports_dynamic_duration()` / `is_cycle_complete()` / `reset_cycle_state()`

**Vegas mode hooks:**
- `get_vegas_display_mode()` — return `VegasDisplayMode` enum (SCROLL/FIXED_SEGMENT/STATIC)
- `get_vegas_content()` — return PIL Image(s) for the scroll stream
- `get_vegas_segment_width()` — width in pixels for FIXED_SEGMENT mode

**Plugin instantiation:** `PluginManager` passes `(plugin_id, config, display_manager, cache_manager, plugin_manager)`.

**Available BasePlugin properties:** `self.plugin_id`, `self.config`, `self.display_manager`, `self.cache_manager`, `self.plugin_manager`, `self.logger`, `self.enabled`, `self.transition_manager`

**Standard plugin config fields** (set in `config/config.json` under the plugin's ID):
```json
{ "enabled": true, "display_duration": 15, "live_priority": false, "high_performance_transitions": false, "transition": {"type": "redraw", "speed": 2, "enabled": true} }
```

**Display dimensions:** Always read dynamically from `self.display_manager.matrix.width` / `.height`, never hardcode.

### PluginManager Internals
Composed of:
- `PluginLoader` — module import and pip dependency installation
- `PluginExecutor` — runs plugin methods with timeout (default 30s) and error isolation
- `PluginStateManager` — plugin state machine (loaded, running, errored, etc.)
- `SchemaManager` — validates plugin config against `config_schema.json`

### Plugin Store
- Store manager: `src/plugin_system/store_manager.py`
- Registry: `https://raw.githubusercontent.com/ChuckBuilds/ledmatrix-plugins/main/plugins.json`
- Official plugins live in the `ledmatrix-plugins` monorepo; installed via ZIP extraction (no `.git`)
- Update detection uses version comparison (manifest `version` vs registry `latest_version`)
- Third-party plugins use their own repo URL with empty `plugin_path`

### Web Interface
Flask app at `web_interface/app.py` with two blueprints in `web_interface/blueprints/`:
- `api_v3.py` — REST API endpoints for plugin management, config, and system control
- `pages_v3.py` — HTMX-driven page routes

SSE streams for real-time UI updates: `/api/v3/stream/stats`, `/stream/display`, `/stream/logs`

### Config System
- `config/config.json` — all user settings (gitignored, created from `config/config.template.json`)
- `config/config_secrets.json` — API keys etc. (gitignored)
- Plugin configs are stored within `config/config.json` under their plugin ID — **not** in the plugin directory, so they survive reinstalls
- `ConfigService` wraps `ConfigManager` to provide hot-reload (env var `LEDMATRIX_HOT_RELOAD`)

### Vegas Mode
`src/vegas_mode/` — A continuous-scroll display mode where plugins render into a shared stream. Plugins declare their behavior via `VegasDisplayMode` enum on `BasePlugin`:
- `SCROLL` — plugin provides multiple frames that scroll through the stream
- `FIXED_SEGMENT` — plugin provides a fixed-width block that scrolls by
- `STATIC` — scroll pauses while plugin displays, then resumes

### Helper Libraries (`src/common/`, `src/base_classes/`)
- `src/common/` — shared utilities: `scroll_helper.py`, `text_helper.py`, `logo_helper.py`, `display_helper.py`, `api_helper.py`, `game_helper.py`
- `src/base_classes/` — sport-specific base classes: `sports.py`, `hockey.py`, `football.py`, `basketball.py`, `baseball.py`

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
- Use `get_logger()` from `src.logging_config` in plugins and core code, not `logging.getLogger()`
- When modifying a plugin in the monorepo, you MUST bump `version` in its `manifest.json` and run `python update_registry.py` — otherwise users won't receive the update
- The `EMULATOR=true` env var switches the `rgbmatrix` import to `RGBMatrixEmulator` in `src/display_manager.py`

## Development Setup for Plugins
```bash
# Set up symlinks from plugin-repos/ to plugins/ for active development
python scripts/setup_plugin_repos.py

# Or use the dev helper to link a plugin repo (e.g., from GitHub or local path)
./dev_plugin_setup.sh link-github <plugin-name>
./dev_plugin_setup.sh link <plugin-name> <path-to-repo>
```
`plugin-repos/` contains development symlinks into the monorepo; `plugins/` is the runtime directory (gitignored).

### Plugin Repo Auto-Versioning (pre-push hook)
Plugin repos should install the pre-push hook so patch versions bump automatically on push:
```bash
# From the plugin repo directory
cp /path/to/LEDMatrix/scripts/git-hooks/pre-push-plugin-version .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```
The hook bumps `manifest.json` patch version and creates a git tag. Use `SKIP_TAG=1` to skip. Version resolution order: GitHub Releases → Tags → Manifest → commit hash.

## Monitoring on Raspberry Pi
```bash
journalctl -u ledmatrix -f        # display service logs
journalctl -u ledmatrix-web -f    # web service logs
```
Service files: `ledmatrix.service`, `ledmatrix-web.service`

## Git Conventions
**Branch naming:** `feature/`, `fix/`, `hotfix/`, `refactor/` + kebab-case description

**Commit format:** `type(scope): description`
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Merge strategy:** Squash and merge preferred for features and fixes. `main` is protected — all changes via PR.
