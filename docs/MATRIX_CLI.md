# Matrix CLI

`matrix` is the LEDMatrix developer CLI. It wraps common development tasks — running the emulator, managing the web interface, scaffolding plugins, and interacting with the plugin store — into a single ergonomic command.

## Installation

From the LEDMatrix project root:

```bash
sudo ln -sf "$(pwd)/scripts/matrix_cli.py" /usr/local/bin/matrix
chmod +x scripts/matrix_cli.py
```

Dependencies (`click`, `rich`, `requests`) are already present in the project venv at `.venv/`. The CLI auto-detects and uses `.venv/bin/python3` when available.

## Quick Start

```bash
matrix run          # start the display in emulator mode
matrix web          # start the web interface on localhost:5000
matrix plugin list  # show all installed plugins
```

---

## Command Reference

### `matrix run`

Start the LED display in emulator mode (no hardware required).

```
matrix run [--debug]
```

| Option | Description |
|--------|-------------|
| `--debug` | Enable verbose debug logging |

**Example:**
```bash
matrix run --debug
```

---

### `matrix web`

Start the web interface on `http://localhost:5000`.

```
matrix web
```

---

### `matrix logs`

Tail live service logs. Requires a systemd host (Raspberry Pi).

```
matrix logs [--service display|web|all]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--service` | `display` | Which service log to tail (`display`, `web`, or `all`) |

**Examples:**
```bash
matrix logs                   # tail the display service log
matrix logs --service web     # tail the web interface log
matrix logs --service all     # tail both logs
```

---

### `matrix service`

Manage LEDMatrix systemd services. Requires `sudo` and a systemd host (Raspberry Pi).

```
matrix service <start|stop|restart|status> [--service display|web|all]
```

| Argument | Description |
|----------|-------------|
| `action` | `start`, `stop`, `restart`, or `status` |

| Option | Default | Description |
|--------|---------|-------------|
| `--service` | `display` | Which service to act on |

**Examples:**
```bash
matrix service restart              # restart the display service
matrix service status --service all # check status of both services
```

---

## Plugin Commands

All plugin subcommands are under `matrix plugin`.

---

### `matrix plugin new`

Scaffold a new plugin with all required files (`manifest.json`, `config_schema.json`, `manager.py`, `requirements.txt`, `.gitignore`) and initialize a git repo with the pre-push versioning hook.

```
matrix plugin new <id> [--path DIR] [--no-interactive]
```

| Option | Description |
|--------|-------------|
| `--path DIR` | Parent directory for the new plugin (default: current directory) |
| `--no-interactive` | Skip prompts and use derived defaults |

**Example:**
```bash
matrix plugin new my-plugin --path ~/projects
```

After scaffolding, link the plugin into the runtime:
```bash
matrix plugin link my-plugin ~/projects/my-plugin
```

---

### `matrix plugin link`

Link a local plugin repo into the display runtime via a symlink in `plugins/` and `plugin-repos/`.

```
matrix plugin link <id> <path>
```

**Example:**
```bash
matrix plugin link my-plugin ~/projects/my-plugin
```

---

### `matrix plugin unlink`

Remove a dev plugin symlink. The repo itself is not deleted.

```
matrix plugin unlink <id>
```

---

### `matrix plugin status`

Show the git status of all linked plugin repos.

```
matrix plugin status
```

---

### `matrix plugin list`

Display a rich table of all installed plugins with their enabled state, version, category, and whether they are dev symlinks.

```
matrix plugin list
```

---

### `matrix plugin render`

Render a plugin to a PNG file without running the full display loop. Useful for quick visual checks.

```
matrix plugin render <id> [-o OUTPUT] [--width W] [--height H] [--skip-update]
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output PNG path (default: `/tmp/plugin_render.png`) |
| `--width` | Override display width in pixels |
| `--height` | Override display height in pixels |
| `--skip-update` | Skip `update()` and render `display()` only |

**Example:**
```bash
matrix plugin render clock-simple -o /tmp/clock.png
```

---

### `matrix plugin install`

Install a plugin from the store or a GitHub URL. **Requires the web interface to be running** (`matrix web`).

```
matrix plugin install <target> [--branch BRANCH]
```

`target` can be a plugin ID (e.g. `clock-simple`) or a full GitHub URL.

| Option | Description |
|--------|-------------|
| `--branch` | Git branch to install from |

**Examples:**
```bash
matrix plugin install clock-simple
matrix plugin install https://github.com/example/my-ledmatrix-plugin
```

---

### `matrix plugin uninstall`

Uninstall a plugin. Prompts for confirmation. **Requires the web interface to be running.**

```
matrix plugin uninstall <id> [--keep-config] [-y]
```

| Option | Description |
|--------|-------------|
| `--keep-config` | Preserve the plugin's `config.json` entry after removal |
| `-y, --yes` | Skip the confirmation prompt |

---

### `matrix plugin update`

Update one plugin or all installed plugins. **Requires the web interface to be running.**

```
matrix plugin update [id]
```

If `id` is omitted, all installed plugins are updated.

**Examples:**
```bash
matrix plugin update clock-simple   # update one plugin
matrix plugin update                # update all plugins
```

---

### `matrix plugin enable` / `matrix plugin disable`

Enable or disable a plugin by editing `config/config.json` directly. **No service required.**

```
matrix plugin enable <id>
matrix plugin disable <id>
```

Changes take effect on the next display loop cycle.

---

### `matrix plugin health`

Show runtime plugin health (state, error count, last error). **Requires the web interface to be running.**

```
matrix plugin health [id]
```

If `id` is omitted, health for all plugins is shown.

---

### `matrix plugin store`

Browse the plugin registry. Optionally filter by name, ID, tag, or category.

```
matrix plugin store [query]
```

**Examples:**
```bash
matrix plugin store             # list all available plugins
matrix plugin store sports      # filter by tag/category
matrix plugin store clock       # filter by name
```

---

## Notes

### Commands requiring the web interface

The following commands call the REST API at `localhost:5000` and require the web interface to be running first:

| Command | Reason |
|---------|--------|
| `matrix plugin install` | Plugin download and extraction via API |
| `matrix plugin uninstall` | Clean uninstall via API |
| `matrix plugin update` | Version check and reinstall via API |
| `matrix plugin health` | Live runtime state from the display loop |

Start the web interface in a separate terminal before running these:
```bash
matrix web
```

### Venv Python

All subprocess calls that invoke `run.py`, `start.py`, or `render_plugin.py` automatically use `.venv/bin/python3` if it exists, falling back to the system Python. No manual activation needed.
