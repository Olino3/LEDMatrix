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
- `web_interface/start.py` → `web_interface/app.py` — Flask web UI (port 5000)

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
Flask app at `web_interface/app.py` with blueprints: `api_v3.py` (REST API) and `pages_v3.py` (HTMX routes). SSE streams: `/api/v3/stream/stats`, `/stream/display`, `/stream/logs`.

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
