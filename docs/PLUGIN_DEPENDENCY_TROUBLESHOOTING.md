# Plugin Dependency Installation Troubleshooting

This guide helps resolve issues with plugin dependency installation in the LEDMatrix system.

## How Dependencies Are Installed

Plugin dependencies are installed automatically at load time by the `PluginLoader` using:

1. **`uv pip install`** (preferred) — fast, reliable, venv-aware
2. **`.venv/bin/python3 -m pip install`** (fallback) — when uv is not available

All installs target the project virtual environment (`.venv/`). The `--break-system-packages` flag is no longer used.

## Common Issues

### Dependencies not installing automatically

**Symptoms:**
- Plugin fails to load with `ModuleNotFoundError`
- No install attempt logged

**Solutions:**

1. **Remove the marker file** to force reinstall:
   ```bash
   rm plugins/PLUGIN-NAME/.dependencies_installed
   sudo systemctl restart ledmatrix
   ```

2. **Install manually** with uv:
   ```bash
   uv pip install -r plugins/PLUGIN-NAME/requirements.txt
   ```

3. **Verify uv is installed:**
   ```bash
   which uv
   # If not found, install: curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### uv not found

If `uv` is not on PATH, the system falls back to pip automatically. To install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via the matrix CLI:
```bash
matrix doctor  # will report uv status
```

### Dependency installation timed out

Default timeout is 300 seconds. For slow networks:

1. Install dependencies manually:
   ```bash
   uv pip install -r plugins/PLUGIN-NAME/requirements.txt
   ```

2. Then restart:
   ```bash
   sudo systemctl restart ledmatrix
   ```

### Permission errors

Since installs target the venv, permission errors are rare. If encountered:

1. Verify venv ownership:
   ```bash
   ls -la .venv/
   ```

2. Fix permissions if needed:
   ```bash
   sudo chown -R $USER:$USER .venv/
   ```

## Checking Installation

```bash
# Verify a package is installed in the venv
.venv/bin/python3 -c "import package_name; print(package_name.__version__)"

# List all installed packages
uv pip list

# Check specific package
uv pip show package_name
```

## Getting Help

1. Check the service logs:
   ```bash
   sudo journalctl -u ledmatrix -f
   ```

2. Run diagnostics:
   ```bash
   matrix doctor
   ```

3. Verify plugin manifest:
   ```bash
   cat plugins/PLUGIN-NAME/manifest.json
   ```

## Related Documentation

- [Plugin Dependency Guide](PLUGIN_DEPENDENCY_GUIDE.md)
