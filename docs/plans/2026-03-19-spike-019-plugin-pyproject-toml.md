# SPIKE-019: Plugin requirements.txt to pyproject.toml Migration

## Executive Summary

Plugins currently declare dependencies in `requirements.txt` files, while the core LEDMatrix project already uses `pyproject.toml`. Migrating plugins to per-plugin `pyproject.toml` files aligns the ecosystem with modern Python packaging standards and unlocks richer metadata (optional deps, Python version bounds, entry-point metadata). This document recommends a phased transition that supports both formats simultaneously, with `requirements.txt` eventually deprecated after one full minor release cycle.

---

## Q1: Minimum pyproject.toml Schema

### Required Fields

Plugins are not standalone installable packages -- they are loaded dynamically by `PluginLoader` via `importlib`. This means the `pyproject.toml` serves primarily as a **dependency declaration** and **metadata file**, not as a build configuration. The schema should therefore be minimal.

| Field | Required? | Purpose |
|---|---|---|
| `[build-system]` | Yes | Required by PEP 517/518; use `hatchling` to match core project |
| `[project].name` | Yes | Package name; use `ledmatrix-plugin-<id>` convention |
| `[project].version` | Yes | Plugin version (mirrors `manifest.json` `version`) |
| `[project].requires-python` | Recommended | Minimum Python version (e.g., `>=3.10`) |
| `[project].dependencies` | Yes | Runtime dependencies (replaces `requirements.txt`) |
| `[project].description` | Optional | One-line description (mirrors manifest `description`) |
| `[project].authors` | Optional | Author info |
| `[project.optional-dependencies]` | Optional | Groups like `dev`, `test` |

### Fields to NOT Include (Avoid Manifest Duplication)

The following metadata already lives in `manifest.json` and should NOT be duplicated in `pyproject.toml`:

- `id` (plugin identity -- the canonical source is `manifest.json`)
- `entry_point` and `class_name` (plugin loader reads these from manifest)
- `display_modes`, `category`, `tags` (display system metadata)
- `update_interval`, `default_duration` (runtime config)

The `version` field is the one deliberate overlap. Both files need it: `pyproject.toml` for packaging tools, `manifest.json` for the plugin loader and registry. A CI check or pre-push hook should enforce they stay in sync.

### Concrete Example

For the `march-madness` plugin:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ledmatrix-plugin-march-madness"
version = "1.0.1"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28.0",
    "Pillow>=9.1.0",
    "pytz>=2022.1",
    "numpy>=1.24.0",
]
```

For the `starlark-apps` plugin:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ledmatrix-plugin-starlark-apps"
version = "1.0.1"
requires-python = ">=3.10"
dependencies = [
    "Pillow>=10.4.0",
    "PyYAML>=6.0.2",
    "requests>=2.32.0",
]
```

For a plugin with no dependencies (like `web-ui-info`):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ledmatrix-plugin-web-ui-info"
version = "1.0.1"
requires-python = ">=3.10"
dependencies = []
```

### Package Naming Convention

Use `ledmatrix-plugin-<plugin-id>` for the `[project].name` field. This:
- Avoids PyPI namespace collisions
- Makes plugin packages discoverable if ever published
- Follows the established `ledmatrix-` prefix convention used in directory naming

---

## Q2: Transition Strategy

### Recommendation: Dual-Format Support for One Minor Release Cycle

**Phase A (v1.2.0): Both formats accepted, `pyproject.toml` preferred**
- `dep_installer.py` and `plugin_loader.py` check for `pyproject.toml` first, fall back to `requirements.txt`
- `matrix plugin new` generates `pyproject.toml` (no `requirements.txt`)
- Existing plugins continue to work with `requirements.txt` unchanged
- Documentation updated to recommend `pyproject.toml` for new plugins
- Deprecation warning logged (once per session) when `requirements.txt` is used without a `pyproject.toml` present

**Phase B (v1.3.0): `requirements.txt` deprecated**
- `requirements.txt`-only plugins still work but trigger a visible deprecation warning
- Plugin validation tool (`validate-plugin` skill) warns on missing `pyproject.toml`

**Phase C (v2.0.0): `requirements.txt` support removed**
- `requirements.txt` fallback code removed from `dep_installer.py`
- Plugin contract updated to require `pyproject.toml`
- Aligns with the Flask-to-FastAPI migration (Phase 2) as a clean breaking change

### Migration Path for Existing Plugins

1. **Automated migration script:** Provide `matrix plugin migrate-deps <plugin-id>` command that:
   - Reads `requirements.txt`
   - Reads `manifest.json` for name/version
   - Generates a `pyproject.toml` with the correct schema
   - Optionally deletes `requirements.txt` (with `--remove-old` flag)
   - Validates the result

2. **Batch migration:** Provide `matrix plugin migrate-deps --all` to migrate all installed plugins at once.

3. **External `ledmatrix-plugins` repo:** Coordinate with SPIKE-003. The `update_registry.py` script (in that repo) should be updated to read dependencies from `pyproject.toml` when present. A single PR to the external repo can migrate all community plugins simultaneously.

### Handling the `manifest.json` `dependencies` Array

The `starlark-apps` manifest already has a `dependencies` array. This is a third location for dependency data. During the transition:
- `pyproject.toml` `[project].dependencies` is the canonical source
- `manifest.json` `dependencies` array becomes informational only (for quick display in the store UI without parsing TOML)
- The migration script should ensure consistency between the two

---

## Q3: dep_installer.py Changes

### Detection Logic

The `install_plugin_dependencies` function currently takes a `requirements_file: Path` parameter. The recommended approach is to add a higher-level function that handles format detection, while keeping the existing function for backwards compatibility.

```python
def install_plugin_deps(
    plugin_dir: Path,
    *,
    plugin_id: str = "",
    timeout: int = 300,
    python_path: Optional[str] = None,
) -> bool:
    """Install dependencies for a plugin, detecting the format automatically.

    Checks for pyproject.toml first, falls back to requirements.txt.
    """
    pyproject_path = plugin_dir / "pyproject.toml"
    requirements_path = plugin_dir / "requirements.txt"

    if pyproject_path.exists():
        return _install_from_pyproject(
            plugin_dir, plugin_id=plugin_id, timeout=timeout,
            python_path=python_path,
        )
    elif requirements_path.exists():
        # Deprecation warning (Phase A)
        logger.warning(
            "Plugin %s uses requirements.txt — migrate to pyproject.toml. "
            "See: matrix plugin migrate-deps %s",
            plugin_id, plugin_id,
        )
        return install_plugin_dependencies(
            requirements_path, plugin_id=plugin_id, timeout=timeout,
            python_path=python_path,
        )
    else:
        logger.debug("No dependency file found for %s", plugin_id)
        return True  # No dependencies needed
```

### uv Commands

| Format | uv command | Pip fallback |
|---|---|---|
| `pyproject.toml` | `uv pip install --no-deps -e <plugin_dir>` or `uv pip install <plugin_dir>` | `pip install <plugin_dir>` |
| `requirements.txt` | `uv pip install -r requirements.txt` (unchanged) | `pip install -r requirements.txt` |

**Important consideration:** Using `uv pip install <plugin_dir>` would install the plugin as a package, which is unnecessary since `PluginLoader` handles module loading via `importlib`. The recommended approach is:

```
uv pip install --no-build-isolation --only-deps <plugin_dir>
```

This tells uv to read `[project].dependencies` from `pyproject.toml` and install only the dependencies, without building/installing the plugin package itself. This is the cleanest approach because:
- It does not install the plugin as a package (avoids conflicts with the dynamic loader)
- It reads dependency specs directly from `pyproject.toml`
- It respects version constraints and Python version bounds

However, `--only-deps` is not currently a uv flag. The practical alternatives are:

**Option 1 (Recommended): Parse and install**
```python
# Read [project].dependencies from pyproject.toml and pass them directly
import tomllib  # Python 3.11+ stdlib, or tomli for 3.10

with open(pyproject_path, "rb") as f:
    data = tomllib.load(f)

deps = data.get("project", {}).get("dependencies", [])
if deps:
    cmd = [uv_path, "pip", "install"] + deps
```

This avoids installing the plugin as a package while still using the `pyproject.toml` as the dependency source. It also means no build system is invoked.

**Option 2: Install as editable, ignore side effects**
```
uv pip install -e <plugin_dir>
```

This would register the plugin as a package in the venv. It works but is conceptually wrong -- the plugin is loaded by `PluginLoader`, not by `import ledmatrix_plugin_march_madness`.

**Recommendation:** Option 1. Parse `[project].dependencies` and pass them to `uv pip install` directly. This is the simplest approach with no side effects.

For Python 3.10 compatibility (which the project requires per `requires-python = ">=3.10"` in the root `pyproject.toml`), use the `tomli` backport package, or add conditional import:

```python
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
```

The `tomli` package should be added to the core project's `[project].dependencies` since it is needed at runtime for plugin loading on Python 3.10.

### Marker File Implications

The current marker file approach (`.dependencies_installed` touched after successful install) works identically for both formats. No changes needed.

However, the marker should be invalidated when `pyproject.toml` changes. Currently the marker is a simple empty file. Consider enhancing it to store a hash of the dependency file:

```python
import hashlib

def _dep_file_hash(plugin_dir: Path) -> str:
    """Compute a hash of the dependency source file."""
    for name in ("pyproject.toml", "requirements.txt"):
        dep_file = plugin_dir / name
        if dep_file.exists():
            return hashlib.sha256(dep_file.read_bytes()).hexdigest()[:16]
    return ""

# On install success:
marker_path.write_text(_dep_file_hash(plugin_dir))

# On check:
if marker_path.exists():
    stored_hash = marker_path.read_text().strip()
    current_hash = _dep_file_hash(plugin_dir)
    if stored_hash == current_hash:
        return True  # Already installed and up to date
    # Else: dependency file changed, reinstall
```

This is a quality-of-life improvement that could be done independently of the pyproject.toml migration but fits naturally into this work.

### plugin_loader.py Changes

`PluginLoader.install_dependencies()` (line 122-152) currently hardcodes `plugin_dir / "requirements.txt"`. It should be updated to call the new `install_plugin_deps(plugin_dir, ...)` function instead, delegating format detection to `dep_installer.py`.

Similarly, `StoreManager._install_dependencies()` (line 1511-1529 of `store_manager.py`) hardcodes `requirements.txt` and should be updated the same way.

---

## Q4: Scaffold Tooling Updates

### `matrix plugin new`

The scaffold command (in `scripts/matrix_cli.py`, line 669-765) currently generates `requirements.txt` with placeholder content. It should be updated to:

1. **Generate `pyproject.toml` instead of `requirements.txt`** (Phase A onward)
2. Use the plugin ID and display name from the interactive prompts to populate the `[project]` section
3. Include the `[build-system]` section with hatchling

Proposed template:

```python
PYPROJECT_TEMPLATE = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ledmatrix-plugin-{id}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    # Add plugin dependencies here, e.g.:
    # "requests>=2.28.0",
]
"""
```

Replace line 740 (`(plugin_dir / "requirements.txt").write_text(REQUIREMENTS_CONTENT)`) with:

```python
(plugin_dir / "pyproject.toml").write_text(PYPROJECT_TEMPLATE.format(id=plugin_id))
```

### `matrix plugin migrate-deps` (New Subcommand)

Add a new CLI subcommand to automate migration for existing plugins:

```
matrix plugin migrate-deps <plugin-id>    # migrate one plugin
matrix plugin migrate-deps --all          # migrate all installed plugins
```

### `validate-plugin` Skill

The validate-plugin skill (`.claude/skills/validate-plugin/SKILL.md`) currently lists `requirements.txt` as a required file in step 2. Update to:

- **Phase A:** Accept either `pyproject.toml` or `requirements.txt`. Warn if only `requirements.txt` is present.
- **Phase C:** Require `pyproject.toml`. Fail if only `requirements.txt` is present.
- Add a new validation step: if both files exist, verify that `[project].dependencies` in `pyproject.toml` matches the contents of `requirements.txt` (or at minimum, warn about potential drift).

### Plugin Contract Documentation

Update `.claude/rules/plugin-dev.md` "Required Files per Plugin" section:

**Phase A:**
```
- `pyproject.toml` (preferred) OR `requirements.txt` -- dependency declaration
```

**Phase C:**
```
- `pyproject.toml` -- dependency and metadata declaration (replaces requirements.txt)
```

---

## Q5: Registry Impact

### `plugins.json` Registry Format

The external `ledmatrix-plugins` repo hosts a `plugins.json` that the store manager fetches from GitHub. The current registry entries (based on `march-madness/manifest.json`) include:

```json
{
  "id": "march-madness",
  "version": "1.0.1",
  "dependencies": {},
  ...
}
```

The `dependencies` field is currently either an empty object (`{}`) or an array of pip requirement strings. This field should continue to exist in the registry for quick dependency display in the store UI. Its values should be derived from `pyproject.toml` when present.

### `update_registry.py` Changes

The `update_registry.py` script (in the external `ledmatrix-plugins` repo, not in this monorepo) needs to:

1. **Read `pyproject.toml` when present** to extract `[project].dependencies`
2. **Fall back to `requirements.txt`** during the transition period
3. **Populate the registry `dependencies` field** from whichever source is found
4. **Optionally add new registry fields:**
   - `requires_python`: from `[project].requires-python` (useful for compatibility checks before install)
   - `dep_format`: `"pyproject.toml"` or `"requirements.txt"` (informational, helps track migration progress)

### New Metadata Flowing into Registry

| pyproject.toml field | Registry field | Purpose |
|---|---|---|
| `[project].dependencies` | `dependencies` (array) | Dependency list for store UI display |
| `[project].requires-python` | `requires_python` | Python version gate before install |
| `[project].version` | `version` (already exists) | Version sync validation |

### Store Manager Changes

`StoreManager` in `src/plugin_system/store_manager.py` needs minimal changes:
- After cloning/installing a plugin, call the new format-aware `install_plugin_deps()` instead of looking for `requirements.txt` directly
- The registry fetch and display logic does not need to change since `dependencies` remains a simple array in the registry

---

## Recommendation

**Proceed with the migration.** The benefits (standards alignment, richer metadata, uv ecosystem compatibility) outweigh the migration cost. The key design decisions are:

1. **Parse-and-install approach** (Option 1 in Q3) -- do not install plugins as packages. Read `[project].dependencies` from `pyproject.toml` and pass them to `uv pip install` directly.

2. **Minimal schema** -- only `[build-system]`, `[project].name`, `version`, `requires-python`, and `dependencies`. Do not duplicate manifest metadata.

3. **Dual-format support** for one minor release cycle (v1.2.0 through v1.3.0), with removal at v2.0.0.

4. **Automated migration tooling** (`matrix plugin migrate-deps`) to minimize burden on plugin authors.

5. **Add `tomli` to core dependencies** for Python 3.10 TOML parsing support.

---

## Proposed Timeline

| Milestone | Version | Work Items |
|---|---|---|
| **Implementation** | v1.2.0 | Update `dep_installer.py` with dual-format support; update `plugin_loader.py` and `store_manager.py` to use new function; add `tomli` dependency; update `matrix plugin new` scaffold; add `matrix plugin migrate-deps` command |
| **Documentation** | v1.2.0 | Update `.claude/rules/plugin-dev.md`; update `validate-plugin` skill; update `CLAUDE.md` required files list |
| **External repo** | v1.2.0 | PR to `ledmatrix-plugins` repo: update `update_registry.py`; migrate all community plugin `requirements.txt` files to `pyproject.toml` |
| **Deprecation** | v1.3.0 | `requirements.txt`-only triggers visible deprecation warning |
| **Removal** | v2.0.0 | Remove `requirements.txt` fallback code; require `pyproject.toml` in plugin contract |

### Estimated Implementation Effort

- `dep_installer.py` changes: ~50 lines added
- `plugin_loader.py` changes: ~5 lines modified
- `store_manager.py` changes: ~10 lines modified
- `matrix_cli.py` scaffold update: ~15 lines modified
- `matrix_cli.py` migrate-deps command: ~80 lines new
- `validate-plugin` skill update: ~10 lines modified
- Tests: ~100 lines new (dep_installer format detection, migration script, marker hash)
- **Total: ~270 lines of changes, spread across 6 files**
