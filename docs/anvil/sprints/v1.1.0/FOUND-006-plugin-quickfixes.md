# FOUND-006 — Plugin Quick-Fixes: `matrix.width` / `matrix.height` References

> **For Claude:** Use `superpowers:writing-plans` before touching plugin files. Read the `ledmatrix-plugins` monorepo structure first. This work happens in the `ledmatrix-plugins` repo, not in the LEDMatrix core repo.

**Status:** Done
**Phase:** v1.1.0 — Foundation
**Type:** Fix
**Depends on:** _(none — fully independent, can be done in parallel with FOUND-001 through FOUND-005)_
**Blocks:** [SPIKE-003](SPIKE-003-monorepo-plugin-quickfixes-pr.md)

---

## Context

The `DisplayManager` singleton exposes two ways to read display dimensions:

| Access | Status | Notes |
|---|---|---|
| `display_manager.matrix.width` | **Wrong** | Accesses the underlying `rgbmatrix` object directly; breaks when `DisplayManager` is used with `RGBMatrixEmulator` or mocked in tests |
| `display_manager.width` | **Correct** | Property on `DisplayManager` that wraps the matrix dimensions safely |

The ROADMAP identifies two official plugins that use the broken pattern:
- `football-scoreboard`
- `hockey-scoreboard`

These plugins live in the `ledmatrix-plugins` monorepo: `https://github.com/ChuckBuilds/ledmatrix-plugins`. They are NOT in this (LEDMatrix core) repository. The fix must be applied there and new versions published.

**Also affected (found in local plugin-repos during investigation):**
- `plugin-repos/starlark-apps/manager.py` lines 231, 803–804 — uses `display_manager.matrix.width` / `.height`
- `plugin-repos/march-madness/manager.py` lines 800–801, 813–814 — same issue
- `plugin-repos/web-ui-info/manager.py` lines 230–231 — same issue

These local plugins should be fixed in the same pass if they are published plugins; if they are development-only, fix them locally and the relevant plugin repo maintainer should merge.

---

## Acceptance Criteria

**ledmatrix-plugins monorepo (football-scoreboard):**
- [ ] All occurrences of `display_manager.matrix.width` replaced with `display_manager.width`
- [ ] All occurrences of `display_manager.matrix.height` replaced with `display_manager.height`
- [ ] `manifest.json` `version` field bumped (patch: e.g., `1.2.3` → `1.2.4`)
- [ ] Plugin tests pass (or no regression introduced)

**ledmatrix-plugins monorepo (hockey-scoreboard):**
- [ ] Same replacements as above
- [ ] `manifest.json` `version` field bumped (patch)

**ledmatrix-plugins monorepo (registry):**
- [ ] `python update_registry.py` run from monorepo root
- [ ] `plugins.json` regenerated with updated versions for both plugins
- [ ] Changes committed and PR opened (or pushed directly if you have push access)

**Local plugin-repos (starlark-apps, march-madness, web-ui-info):**
- [ ] Same replacements applied in each affected file
- [ ] If these are tracked in their own repos, commit and bump versions there too

---

## Implementation Checklist

### 1. Set up the ledmatrix-plugins monorepo locally

- [ ] Check if the monorepo is already cloned anywhere: `find ~ -name "plugins.json" -path "*/ledmatrix-plugins/*" 2>/dev/null`
- [ ] If not, clone it: `git clone https://github.com/ChuckBuilds/ledmatrix-plugins /tmp/ledmatrix-plugins`
- [ ] Create a feature branch: `git -C /tmp/ledmatrix-plugins checkout -b fix/display-manager-width-height`

### 2. Audit all width/height references in the monorepo

```bash
grep -rn "display_manager\.matrix\.width\|display_manager\.matrix\.height" \
    /tmp/ledmatrix-plugins/ \
    --include="*.py"
```

- [ ] Record every file and line number
- [ ] The ROADMAP names `football-scoreboard` and `hockey-scoreboard` specifically — confirm these appear in the grep output
- [ ] If additional plugins appear in the grep output beyond these two, note them and include the same fix

### 3. Fix football-scoreboard

**File:** `football-scoreboard/manager.py` (or equivalent — exact path may differ)

For each occurrence:
```python
# BEFORE
width = self.display_manager.matrix.width
height = self.display_manager.matrix.height

# AFTER
width = self.display_manager.width
height = self.display_manager.height
```

Replacement is purely mechanical — no logic change, just the property path.

- [ ] Run the project's existing tests for football-scoreboard if any exist: `pytest football-scoreboard/` (may not exist — check)
- [ ] Bump `football-scoreboard/manifest.json` version:
  ```json
  "version": "X.Y.Z+1"
  ```
  (increment the patch component only)

### 4. Fix hockey-scoreboard

- [ ] Same pattern as football-scoreboard
- [ ] Bump `hockey-scoreboard/manifest.json` version

### 5. Fix any other affected plugins found in step 2

- [ ] Apply the same replacement to any additional plugins identified by the audit grep

### 6. Regenerate the registry

```bash
cd /tmp/ledmatrix-plugins
python update_registry.py
```

- [ ] Verify `plugins.json` now contains updated version numbers for all affected plugins
- [ ] `git diff plugins.json` — confirm only version fields changed

### 7. Fix local plugin-repos

**starlark-apps** (`plugin-repos/starlark-apps/manager.py`):

Line 231 (logging statement — lower priority but still wrong):
```python
# BEFORE
f"Display size: {self.display_manager.matrix.width}x{self.display_manager.matrix.height}, "

# AFTER
f"Display size: {self.display_manager.width}x{self.display_manager.height}, "
```

Lines 803–804 (active dimension reads):
```python
# BEFORE
width = self.display_manager.matrix.width
height = self.display_manager.matrix.height

# AFTER
width = self.display_manager.width
height = self.display_manager.height
```

**march-madness** (`plugin-repos/march-madness/manager.py`):

Lines 800–801:
```python
matrix_w = self.display_manager.width
matrix_h = self.display_manager.height
```

Lines 813–814:
```python
w = self.display_manager.width
h = self.display_manager.height
```

**web-ui-info** (`plugin-repos/web-ui-info/manager.py`):

Lines 230–231:
```python
width = self.display_manager.width
height = self.display_manager.height
```

- [ ] For each local plugin repo, bump its `manifest.json` version (patch)
- [ ] Run `python update_registry.py` from the LEDMatrix root if these plugins are tracked in the main registry
- [ ] Commit each fix in the respective repo

### 8. Commit the ledmatrix-plugins monorepo changes

```bash
cd /tmp/ledmatrix-plugins
git add football-scoreboard/ hockey-scoreboard/ plugins.json
# (add any other plugins fixed in step 5)
git commit -m "fix: replace display_manager.matrix.width/height with display_manager.width/height

Use the correct DisplayManager properties instead of accessing the underlying
matrix object directly. This fixes compatibility with RGBMatrixEmulator and
prevents attribute errors when display_manager is mocked in tests.

Fixes: football-scoreboard, hockey-scoreboard (and any others found in audit)
"
git push origin fix/display-manager-width-height
# Open PR to main
```

### 9. Commit local plugin-repos changes

```bash
# In each affected plugin repo:
git add manager.py manifest.json
git commit -m "fix: replace display_manager.matrix.width/height with correct properties"
```

---

## Verification Steps

```bash
# 1. No matrix.width/height refs remain in the fixed plugins (ledmatrix-plugins monorepo)
grep -rn "display_manager\.matrix\.width\|display_manager\.matrix\.height" \
    /tmp/ledmatrix-plugins/ --include="*.py" \
    && echo "FAIL: references remain" || echo "OK: all references fixed"

# 2. No matrix.width/height refs remain in local plugin-repos
grep -rn "display_manager\.matrix\.width\|display_manager\.matrix\.height" \
    plugin-repos/ --include="*.py" \
    && echo "FAIL: references remain" || echo "OK: all references fixed"

# 3. manifest.json versions are bumped (football-scoreboard example)
python3 -c "
import json
mf = json.loads(open('/tmp/ledmatrix-plugins/football-scoreboard/manifest.json').read())
print('football-scoreboard version:', mf['version'])
"

# 4. plugins.json reflects new versions
python3 -c "
import json
registry = json.loads(open('/tmp/ledmatrix-plugins/plugins.json').read())
for plugin_id in ['football-scoreboard', 'hockey-scoreboard']:
    if plugin_id in registry:
        print(plugin_id, 'latest_version:', registry[plugin_id].get('latest_version', registry[plugin_id].get('version', '?')))
"

# 5. Smoke test with emulator: confirm starlark-apps and march-madness still load
EMULATOR=true python3 scripts/render_plugin.py starlark-apps 2>&1 | head -20
EMULATOR=true python3 scripts/render_plugin.py march-madness 2>&1 | head -20
```

---

## Notes

- The `display_manager.width` property is defined in `src/display_manager.py`. Before making changes, confirm it exists: `grep -n "def width" src/display_manager.py`.
- The `display_manager.matrix` attribute is the raw `rgbmatrix.RGBMatrix` (or emulator) object. Direct access is fragile — it bypasses any `DisplayManager` abstraction and makes mocking harder. The property `display_manager.width` is the intended API per `CLAUDE.md`.
- If a plugin has a `test/` directory in the monorepo, run its tests after fixing. If tests break (unexpected), investigate before pushing.
- The `update_registry.py` script is in the `ledmatrix-plugins` repo root. Confirm it generates a valid JSON structure before committing.
- Version bump is patch only (e.g., `1.3.0` → `1.3.1`). Do not bump minor or major — this is a non-breaking fix.
- The pre-push version hook (`scripts/git-hooks/pre-push-plugin-version`) may auto-bump the version on push if installed in the plugin repos. Check if it is installed: `cat /tmp/ledmatrix-plugins/football-scoreboard/.git/hooks/pre-push 2>/dev/null`. If so, you may not need to manually bump `manifest.json`.
