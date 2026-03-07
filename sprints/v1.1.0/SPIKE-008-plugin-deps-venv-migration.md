# SPIKE-008 — Plugin Dependency Installation: Migrate to Venv

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** [FOUND-002](FOUND-002-venv-bootstrap.md)
**Blocks:** _(none)_

---

## Context

With FOUND-002, all core Python execution now runs from `.venv/bin/python3`. However, per-plugin dependency installation still uses system pip via two paths:

1. **`scripts/install_plugin_dependencies.sh`** — iterates through `plugins/*/requirements.txt` and installs each using `pip3 install --break-system-packages`. On Pi (root), it installs system-wide; otherwise it uses `--user`.

2. **`src/plugin_system/plugin_loader.py`** — the `PluginLoader` calls `sys.executable -m pip install --break-system-packages --no-cache-dir -r requirements.txt` when loading a plugin whose deps are not yet installed.

3. **`src/plugin_system/store_manager.py`** — the `PluginStoreManager` calls `pip3 install --break-system-packages -r requirements.txt` after installing or updating a plugin from the store.

Now that the display service runs from `.venv/bin/python3`, `sys.executable` inside the venv points to the venv Python, so `pip install` targets the venv — but the `--break-system-packages` flag is unnecessary and the approach bypasses `uv`.

## Questions Answered

1. **Should plugin deps be installed via `uv pip install -r requirements.txt` instead of `pip install`?**
   Yes — all three code paths now use `uv pip install` when uv is available.

2. **Should `--break-system-packages` be removed now that we target the venv?**
   Yes — removed from all code paths. It was a no-op inside the venv.

3. **Should `scripts/install_plugin_dependencies.sh` be updated to use the venv python / uv, or deprecated in favor of the Python-based PluginLoader approach?**
   Deprecated — the script is now a thin wrapper that prints a deprecation notice and directs users to `uv pip install` for manual installs.

4. **Should plugin `requirements.txt` files eventually migrate to per-plugin `pyproject.toml`?**
   Yes — tracked in [SPIKE-019](SPIKE-019-plugin-pyproject-toml-migration.md).

5. **How does this interact with the plugin store install/update flow via the web API?**
   `StoreManager._install_dependencies` now uses the same `_build_pip_install_cmd()` helper, so the store install/update flow is consistent.

---

## Acceptance Criteria

- [x] All plugin dependency installation paths use `uv pip install` (with pip fallback)
- [x] `--break-system-packages` flag removed from all code paths
- [x] `scripts/install_plugin_dependencies.sh` deprecated with wrapper
- [x] Plugin store install/update flow updated to match
- [x] Tests verify uv usage across all three installation paths

---

## Implementation

A shared `_build_pip_install_cmd()` helper was added to `plugin_loader.py` that:
- Checks for `uv` via `shutil.which("uv")`
- Returns `[uv_path, "pip", "install", "-r", requirements_file]` when uv is available
- Falls back to `[sys.executable, "-m", "pip", "install", "-r", requirements_file]` otherwise

All three consumers now call this helper:
- `PluginLoader.install_dependencies()` — called during plugin load
- `PluginManager._install_plugin_dependencies()` — called during plugin discovery
- `PluginStoreManager._install_dependencies()` — called during store install/update

## Follow-up

- [SPIKE-019](SPIKE-019-plugin-pyproject-toml-migration.md) — Migrate plugin `requirements.txt` to per-plugin `pyproject.toml`

---

## Files Updated

- `src/plugin_system/plugin_loader.py` — added `_build_pip_install_cmd()`, updated `install_dependencies()`
- `src/plugin_system/plugin_manager.py` — updated `_install_plugin_dependencies()` to use shared helper
- `src/plugin_system/store_manager.py` — updated `_install_dependencies()` to use shared helper
- `scripts/install_plugin_dependencies.sh` — replaced with deprecation wrapper
- `test/test_plugin_deps_uv.py` — new tests for uv-based installation

---

## Notes

- This spike was identified during FOUND-002 implementation
- The `--break-system-packages` flag was a no-op inside a venv but confusing to leave in place
- Plugin authors still provide `requirements.txt` in their repos — that contract remains stable
- Documentation updates for `--break-system-packages` references in docs/ are deferred to a separate docs cleanup pass
