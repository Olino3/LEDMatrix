---
name: scaffold-plugin
description: Scaffold a new LEDMatrix plugin with all required files following the plugin contract
user-invocable: true
---

# Scaffold Plugin

Creates a new plugin directory with all required files following the plugin development contract defined in `.claude/rules/plugin-dev.md`.

## Arguments

- `plugin-id` (required) — kebab-case identifier (e.g., `weather-forecast`)
- `plugin-name` (required) — human-readable name (e.g., `Weather Forecast`)
- `description` (optional) — one-line description of what the plugin displays
- `display-modes` (optional) — comma-separated list of display modes (default: `default`)

## Procedure

### 1. Validate inputs

- Confirm `plugin-id` is kebab-case (lowercase letters, numbers, hyphens only)
- Confirm `plugins/<plugin-id>/` does not already exist
- Derive `class_name` from `plugin-id` by converting to PascalCase (e.g., `weather-forecast` -> `WeatherForecast`)

### 2. Create plugin directory

Create `plugins/<plugin-id>/` with these four required files:

#### `manifest.json`
```json
{
  "id": "<plugin-id>",
  "name": "<plugin-name>",
  "version": "1.0.0",
  "description": "<description or 'A LEDMatrix plugin'>",
  "entry_point": "manager",
  "class_name": "<ClassName>",
  "display_modes": ["<display-modes or 'default'>"]
}
```

#### `config_schema.json`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": false,
      "description": "Enable or disable this plugin"
    },
    "display_duration": {
      "type": "integer",
      "default": 15,
      "minimum": 5,
      "description": "How long to display this plugin (seconds)"
    },
    "transition": {
      "type": "object",
      "properties": {
        "type": { "type": "string", "default": "redraw", "enum": ["redraw", "scroll_up", "scroll_down", "scroll_left", "scroll_right", "fade"] },
        "speed": { "type": "integer", "default": 2, "minimum": 1, "maximum": 10 },
        "enabled": { "type": "boolean", "default": true }
      }
    }
  },
  "required": ["enabled"]
}
```

#### `manager.py`
```python
from src.plugin_system.base_plugin import BasePlugin
from src.logging_config import get_logger

logger = get_logger(__name__)


class <ClassName>(BasePlugin):
    """<plugin-name> plugin for LEDMatrix."""

    def update(self):
        """Fetch or compute data to display."""
        pass

    def display(self, force_clear=False):
        """Render content to the LED matrix."""
        pass
```

#### `requirements.txt`
Create as an empty file.

### 3. Update config template

Read `config/config.template.json` and add a default config section for the new plugin:

```json
"<plugin-id>": {
  "enabled": false,
  "display_duration": 15,
  "transition": {
    "type": "redraw",
    "speed": 2,
    "enabled": true
  }
}
```

### 4. Post-creation reminders

Print:
- `Plugin scaffolded at plugins/<plugin-id>/`
- `Next steps:`
  - `1. Implement update() and display() in manager.py`
  - `2. Add any pip dependencies to requirements.txt`
  - `3. Add plugin-specific config fields to config_schema.json`
  - `4. Run: python update_registry.py`

## References

- `.claude/rules/plugin-dev.md` — full plugin contract
- `src/plugin_system/base_plugin.py` — BasePlugin class
- `config/config.template.json` — config template to update
