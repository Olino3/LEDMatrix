# SPIKE-019 — Migrate Plugin `requirements.txt` to Per-Plugin `pyproject.toml`

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** [SPIKE-008](SPIKE-008-plugin-deps-venv-migration.md)
**Blocks:** _(none)_

---

## Context

With SPIKE-008, plugin dependency installation was migrated to `uv pip install` targeting the project venv. Plugins still declare dependencies in `requirements.txt` files. The modern Python packaging standard is `pyproject.toml`, and `uv` natively supports it.

Migrating plugins to per-plugin `pyproject.toml` would:
- Allow richer metadata (version constraints, optional deps, Python version bounds)
- Align with the core project's `pyproject.toml` approach (FOUND-001)
- Enable future use of `uv` workspace features for plugin dependency resolution
- Support eventual plugin versioning and publishing via PyPI-compatible tooling

## Questions to Answer

1. What is the minimum `pyproject.toml` schema needed for plugins? (name, version, dependencies, entry-point metadata?)
2. Should the plugin contract require `pyproject.toml` or accept both `requirements.txt` and `pyproject.toml` during a transition period?
3. How does `dep_installer.py` need to change to support `pyproject.toml`-based installs?
4. Should plugin scaffold tooling (`scaffold-plugin` skill) generate `pyproject.toml` instead of/alongside `requirements.txt`?
5. How does this affect the plugin store registry (`plugins.json`) and `update_registry.py`?

## Files to Investigate

| File | Relevance |
|------|-----------|
| `src/plugin_system/dep_installer.py` | Would need to detect and handle `pyproject.toml` |
| `src/plugin_system/plugin_loader.py` | Marker file logic may need updating |
| `plugins/*/requirements.txt` | Current dependency declaration files |
| `plugins/*/manifest.json` | May absorb some `pyproject.toml` metadata |
| `.claude/rules/plugin-dev.md` | Plugin contract documentation |

## Expected Outcome

A recommendation and/or implementation that:
- Defines the per-plugin `pyproject.toml` schema
- Updates `dep_installer.py` to handle both formats
- Provides a migration path for existing plugins
- Updates plugin scaffold tooling

## Notes

- This spike was identified during SPIKE-008 implementation
- `requirements.txt` support should remain during transition for backwards compatibility
- Plugin authors in the external `ledmatrix-plugins` repo would need to be migrated (coordinate with SPIKE-003)
