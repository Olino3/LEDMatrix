---
name: validate-plugin
description: Validate a LEDMatrix plugin directory against the plugin contract (manifest, schema, BasePlugin, architecture rules)
user-invocable: true
---

# Validate Plugin

Validates a plugin directory against the full plugin development contract defined in `.claude/rules/plugin-dev.md`.

## Arguments

- `plugin-id` (required) — the plugin directory name under `plugins/` (e.g., `weather-forecast`)

## Procedure

### 1. Locate plugin directory

Check that `plugins/<plugin-id>/` exists. If not, check `plugin-repos/<plugin-id>/` (dev symlink). If neither exists, report error and stop.

### 2. Check required files

Verify all four required files exist:
- `manifest.json`
- `config_schema.json`
- `manager.py`
- `requirements.txt`

Report any missing files as FAIL.

### 3. Validate manifest.json

Read `manifest.json` and verify:
- `id` field matches the directory name (`<plugin-id>`)
- `name` field is present and non-empty
- `version` field is present and follows semver (e.g., `1.0.0`)
- `entry_point` field equals `"manager"`
- `class_name` field is present and is a valid PascalCase identifier
- `display_modes` field is a non-empty array of strings

### 4. Validate config_schema.json

Read `config_schema.json` and verify:
- Has `"$schema": "http://json-schema.org/draft-07/schema#"`
- Has `"type": "object"`
- Has `"properties"` object containing at least `"enabled"` with type `"boolean"`
- `"required"` array includes `"enabled"`

### 5. Validate manager.py

Read `manager.py` and verify:
- Imports `BasePlugin` from `src.plugin_system.base_plugin`
- Uses `get_logger` from `src.logging_config` (not `logging.getLogger`)
- Defines a class matching `class_name` from manifest
- Class inherits from `BasePlugin`
- Class implements `update(self)` method
- Class implements `display(self, force_clear=False)` method
- Does NOT hardcode display dimensions (no literal `64`, `32`, `128` used as width/height — should use `self.display_manager.width` / `.height`)
- Does NOT use `self.display_manager.matrix.width` or `.matrix.height`

### 6. Check optional lifecycle hooks

Report (INFO, not FAIL) which optional hooks are implemented:
- `validate_config()`
- `on_config_change()`
- `on_enable()` / `on_disable()`
- `cleanup()`
- `has_live_priority()` / `has_live_content()` / `get_live_modes()`
- `get_vegas_display_mode()` / `get_vegas_content()` / `get_vegas_segment_width()`

### 7. Check config template

Read `config/config.template.json` and verify the plugin has an entry under its `plugin-id` key.

### 8. Generate report

```
Plugin Validation Report
========================
Plugin: <plugin-id>
Path: <path>

## Required Files
| File | Status |
|---|---|
| manifest.json | PASS/FAIL |
| config_schema.json | PASS/FAIL |
| manager.py | PASS/FAIL |
| requirements.txt | PASS/FAIL |

## Manifest Checks
- id matches directory: PASS/FAIL
- version is semver: PASS/FAIL
- entry_point is "manager": PASS/FAIL
- class_name is PascalCase: PASS/FAIL
- display_modes is non-empty array: PASS/FAIL

## Schema Checks
- Draft-07 schema reference: PASS/FAIL
- "enabled" property exists: PASS/FAIL
- "enabled" in required: PASS/FAIL

## Code Checks
- Imports BasePlugin: PASS/FAIL
- Uses get_logger(): PASS/FAIL
- Class matches manifest class_name: PASS/FAIL
- Inherits BasePlugin: PASS/FAIL
- Implements update(): PASS/FAIL
- Implements display(): PASS/FAIL
- No hardcoded dimensions: PASS/FAIL
- No .matrix.width/height: PASS/FAIL

## Optional Hooks
- <hook>: implemented / not implemented

## Config Template
- Entry in config.template.json: PASS/FAIL

## Verdict: PASS / FAIL (<N> issues found)
```

## References

- `.claude/rules/plugin-dev.md` — full plugin contract
- `src/plugin_system/base_plugin.py` — BasePlugin class
- `config/config.template.json` — config template
