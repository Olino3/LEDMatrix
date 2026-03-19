# Plugin Dependency Installation Guide

## Overview

The LEDMatrix system automatically installs plugin dependencies at load time using `uv pip install` (with a pip fallback). All installs target the project virtual environment (`.venv/`), eliminating the need for system-wide package installation or `--break-system-packages`.

## How It Works

### Automatic Installation

When a plugin is loaded (via display service startup, web UI install, or plugin store update), the `PluginLoader` checks for a `requirements.txt` in the plugin directory and installs dependencies using:

1. **`uv pip install -r requirements.txt`** (preferred — fast, reliable)
2. **`.venv/bin/python3 -m pip install -r requirements.txt`** (fallback if uv not found)

A `.dependencies_installed` marker file is created after successful installation to avoid re-running on subsequent loads.

### No More `--break-system-packages`

Since all installs now target the project venv, the `--break-system-packages` flag is no longer needed or used. The venv is the single source of truth for Python packages.

## Common Scenarios

### Scenario 1: Normal Production Use (Recommended)

**What:** Services running via systemd

```bash
sudo systemctl start ledmatrix
sudo systemctl start ledmatrix-web
```

- **Runs from:** `.venv/bin/python3`
- **Installs to:** `.venv/` (accessible to all services)
- **Result:** Works perfectly, all dependencies accessible

### Scenario 2: Web Interface Plugin Installation

**What:** Installing/enabling plugins via web interface

- **Web service uses:** `.venv/bin/python3`
- **Installs to:** `.venv/`
- **Result:** Works perfectly

### Scenario 3: Development / Emulator Mode

```bash
EMULATOR=true python3 run.py
```

- Dependencies install into the active venv
- Works the same as production

## Manual Dependency Installation

If automatic installation fails, use one of these approaches:

### Option 1: Using uv (Recommended)

```bash
cd /home/ledpi/LEDMatrix
uv pip install -r plugins/PLUGIN-NAME/requirements.txt
```

### Option 2: Using venv pip

```bash
cd /home/ledpi/LEDMatrix
.venv/bin/python3 -m pip install -r plugins/PLUGIN-NAME/requirements.txt
```

### Option 3: Restart the service

Dependencies install automatically at startup:

```bash
sudo systemctl restart ledmatrix
```

## Troubleshooting

### Plugin dependencies not installing

1. Verify `uv` is installed: `which uv`
2. Verify the venv exists: `ls .venv/bin/python3`
3. Check plugin has a `requirements.txt`: `cat plugins/PLUGIN-NAME/requirements.txt`
4. Check logs: `sudo journalctl -u ledmatrix -f`

### Force reinstall

Remove the marker file to force dependency reinstallation:

```bash
rm plugins/PLUGIN-NAME/.dependencies_installed
sudo systemctl restart ledmatrix
```

## For Plugin Developers

When creating plugins with dependencies:

1. **Keep requirements minimal**: Only include essential packages
2. **Test installation**: Verify your `requirements.txt` works with:
   ```bash
   uv pip install -r requirements.txt
   ```
3. **Document dependencies**: Note any system packages needed (via apt)
4. **Future**: Plugin `requirements.txt` will migrate to per-plugin `pyproject.toml`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LEDMatrix Services                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  All services run from .venv/bin/python3                     │
│  ├── Plugin deps installed via uv pip install                │
│  ├── Targeting .venv/ (no system-wide installs)              │
│  └── Accessible to all services and users                    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  dep_installer.py (centralised installer)                    │
│  ├── _find_uv() — locates uv binary                         │
│  ├── _build_install_command() — constructs command           │
│  └── install_plugin_dependencies() — runs installation       │
│                                                              │
│  Used by: PluginLoader, PluginManager, StoreManager          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Deprecated

- `scripts/install_plugin_dependencies.sh` — deprecated in favor of automatic Python-based installation
- `--break-system-packages` flag — no longer needed with venv-based installs
- System-wide pip installs — replaced by venv-targeted installs

## Files to Reference

- Dependency installer: `src/plugin_system/dep_installer.py`
- Plugin loader: `src/plugin_system/plugin_loader.py`
- Store manager: `src/plugin_system/store_manager.py`
- Plugin manager: `src/plugin_system/plugin_manager.py`
