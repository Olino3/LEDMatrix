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

Now that the display service runs from `.venv/bin/python3`, `sys.executable` inside the venv points to the venv Python, so `pip install` targets the venv — but the `--break-system-packages` flag is unnecessary and the approach bypasses `uv`.

## Questions to Answer

1. Should plugin deps be installed via `uv pip install -r requirements.txt` instead of `pip install`?
2. Should `--break-system-packages` be removed now that we target the venv?
3. Should `scripts/install_plugin_dependencies.sh` be updated to use the venv python / uv, or deprecated in favor of the Python-based PluginLoader approach?
4. Should plugin `requirements.txt` files eventually migrate to per-plugin `pyproject.toml`?
5. How does this interact with the plugin store install/update flow via the web API?

## Files to Investigate

| File | Current Behavior |
|------|-----------------|
| `scripts/install_plugin_dependencies.sh` | Uses `pip3 install --break-system-packages` for each plugin's `requirements.txt` |
| `src/plugin_system/plugin_loader.py` | Uses `sys.executable -m pip install --break-system-packages` at plugin load time |
| `docs/PLUGIN_DEPENDENCY_GUIDE.md` | References `sudo pip3 install --break-system-packages` |
| `docs/PLUGIN_DEPENDENCY_TROUBLESHOOTING.md` | References `--break-system-packages` and `/root/.local` troubleshooting |
| `docs/TROUBLESHOOTING.md` (lines 430-431) | References `pip3 install --break-system-packages` for manual plugin dep install |

## Expected Outcome

A recommendation document (or direct implementation) that:
- Updates plugin dep installation to use venv-aware commands
- Removes `--break-system-packages` flags
- Ensures compatibility with the plugin store install/update workflow
- Updates relevant documentation

## Outcome

### Decisions

1. **Use `uv pip install`** — all plugin deps now install via `uv pip install -r requirements.txt` with automatic fallback to `sys.executable -m pip install` when uv is not available.
2. **Remove `--break-system-packages`** — no longer needed since all installs target the project venv.
3. **Deprecate `scripts/install_plugin_dependencies.sh`** — replaced with Python-based `dep_installer` module. Shell script now shows deprecation notice but still works as a thin wrapper.
4. **Per-plugin `pyproject.toml`** — future work (see SPIKE-019). Plugin `requirements.txt` contract remains stable for now.
5. **Plugin store install/update flow** — `StoreManager._install_dependencies` updated to use the same `dep_installer` module.

### Changes Made

| File | Change |
|------|--------|
| `src/plugin_system/dep_installer.py` | **New** — centralised dependency installer with `_find_uv()`, `_build_install_command()`, `install_plugin_dependencies()` |
| `src/plugin_system/plugin_loader.py` | Updated `install_dependencies()` to delegate to `dep_installer` |
| `src/plugin_system/plugin_manager.py` | Updated `_install_plugin_dependencies()` to delegate to `dep_installer` |
| `src/plugin_system/store_manager.py` | Updated `_install_dependencies()` to delegate to `dep_installer` |
| `scripts/install_plugin_dependencies.sh` | Deprecated — now shows deprecation notice with uv-based fallback |
| `docs/PLUGIN_DEPENDENCY_GUIDE.md` | Rewritten for uv/venv approach |
| `docs/PLUGIN_DEPENDENCY_TROUBLESHOOTING.md` | Rewritten for uv/venv approach |
| `docs/TROUBLESHOOTING.md` | Updated manual install command |
| `test/test_plugin_deps.py` | **New** — 16 tests covering dep_installer module and integration |

### Follow-up Work

- **SPIKE-019** (new) — Migrate plugin `requirements.txt` to per-plugin `pyproject.toml`

## Notes

- This spike was identified during FOUND-002 implementation
- The `--break-system-packages` flag becomes a no-op inside a venv but is confusing to leave in place
- Plugin authors still provide `requirements.txt` in their repos — that contract remains stable until SPIKE-019
