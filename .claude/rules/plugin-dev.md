# Plugin Development Contract

## Required Files per Plugin

Every plugin directory (`plugins/<plugin-id>/`) must contain:
- `manifest.json` — id, name, version, description, entry_point, class_name, display_modes
- `config_schema.json` — JSON Schema Draft-7 for plugin config
- `manager.py` — class inheriting `BasePlugin`
- `requirements.txt`

## Required Class Contract

```python
from src.plugin_system.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def update(self):          # fetch data, called on update interval
        ...
    def display(self, force_clear=False):  # render to LED matrix
        ...
```

## Display Dimensions

- NEVER hardcode dimensions — always use `self.display_manager.width` / `self.display_manager.height`

## Optional Lifecycle Hooks

- `validate_config()` — validate config at load time
- `on_config_change()` — called when config updated via web API
- `on_enable()` / `on_disable()` — called when plugin toggled
- `cleanup()` — release resources on unload

## Live Priority Hooks

- `has_live_priority()` — returns True if live priority enabled in config
- `has_live_content()` — return True when live/urgent content available
- `get_live_modes()` — list of display modes active during live takeover

## Vegas Mode Hooks

- `get_vegas_display_mode()` — return `VegasDisplayMode` enum (SCROLL/FIXED_SEGMENT/STATIC)
- `get_vegas_content()` — return PIL Image(s) for scroll stream
- `get_vegas_segment_width()` — width in pixels for FIXED_SEGMENT mode

## Monorepo Plugins

When modifying a plugin in the monorepo:
1. Bump `version` in `manifest.json`
2. Run `python update_registry.py` — otherwise users won't see the update

## Config Storage

Plugin configs live in `config/config.json` under the plugin ID — NOT in the plugin directory. This ensures configs survive reinstalls.

## Known Gotchas

- paho-mqtt 2.x: use `callback_api_version=mqtt.CallbackAPIVersion.VERSION1` for v1 compat
- Plugin instantiation signature: `(plugin_id, config, display_manager, cache_manager, plugin_manager)`
- Use `get_logger()` from `src.logging_config` — never `logging.getLogger()`

## Dev Workflow

```bash
# Link a plugin repo for active development
./dev_plugin_setup.sh link <plugin-name> <path-to-repo>

# Install pre-push auto-versioning hook (in plugin repo)
cp /path/to/LEDMatrix/scripts/git-hooks/pre-push-plugin-version .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```
