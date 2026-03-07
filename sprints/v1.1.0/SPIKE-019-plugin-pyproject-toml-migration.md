# SPIKE-019 — Migrate Plugin `requirements.txt` to Per-Plugin `pyproject.toml`

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** [SPIKE-008](SPIKE-008-plugin-deps-venv-migration.md)
**Blocks:** _(none)_

---

## Context

With SPIKE-008, plugin dependency installation now uses `uv pip install -r requirements.txt`. However, the modern Python packaging convention is `pyproject.toml`, which `uv` natively supports.

Migrating each plugin's `requirements.txt` to a `pyproject.toml` would:
- Align with the core project's packaging approach (already using `pyproject.toml` + `uv`)
- Enable richer plugin metadata (version, description, Python version constraints)
- Allow `uv` to resolve dependencies more intelligently
- Prepare for potential future plugin isolation (per-plugin venvs)

## Questions to Answer

1. What should the minimal `pyproject.toml` look like for a plugin?
2. Should the `PluginLoader` support both `pyproject.toml` and `requirements.txt` during a transition period?
3. Should `uv pip install -e plugins/<plugin-id>` be used to install plugins in editable mode?
4. How does this affect the plugin scaffolding tool (`scaffold-plugin` skill)?
5. Should the plugin store validate `pyproject.toml` structure on install?

## Scope

- Define a standard per-plugin `pyproject.toml` template
- Update `PluginLoader._build_pip_install_cmd()` to detect and prefer `pyproject.toml`
- Update `scaffold-plugin` to generate `pyproject.toml` instead of `requirements.txt`
- Update plugin development documentation
- Migrate existing monorepo plugins (coordinate with SPIKE-003)

## Notes

- `requirements.txt` must remain supported as a fallback for backwards compatibility during the transition
- This is a non-breaking change — plugins without `pyproject.toml` continue to work
- Per-plugin `pyproject.toml` is distinct from per-plugin venvs (that would be Phase 6 DI work)
