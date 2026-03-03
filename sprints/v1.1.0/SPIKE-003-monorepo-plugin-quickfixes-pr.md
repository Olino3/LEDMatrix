# SPIKE-003 — Open PR for `display_manager.matrix.width/height` Fixes in ledmatrix-plugins Monorepo

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** FOUND-006 (local fixes complete)
**Blocks:** _(none)_
**Created from:** FOUND-006 — scope expansion discovered during audit

---

## Context

FOUND-006 identified `football-scoreboard` and `hockey-scoreboard` as the two plugins in the `ledmatrix-plugins` monorepo (`https://github.com/ChuckBuilds/ledmatrix-plugins`) needing `display_manager.matrix.width/height` → `display_manager.width/height` fixes.

During the FOUND-006 audit, **20 plugins** (not 2) were found to use the broken pattern across **39 Python files**. A complete fix was prepared in a local clone at `/tmp/ledmatrix-plugins` on branch `fix/display-manager-width-height`, but could not be committed/pushed from the CI environment due to commit signing restrictions.

---

## Scope

The fix is fully mechanical: replace `display_manager.matrix.width` → `display_manager.width` and `display_manager.matrix.height` → `display_manager.height` across all plugin Python files in the monorepo, bump manifest versions (patch), and regenerate `plugins.json`.

### Affected Plugins (20)

| Plugin | Old Version | New Version | Files Changed |
|---|---|---|---|
| baseball-scoreboard | 1.5.4 | 1.5.5 | logo_manager.py, manager.py, scroll_display.py, sports.py |
| basketball-scoreboard | 1.5.4 | 1.5.5 | basketball.py, manager.py, scroll_display.py, sports.py |
| calendar | 1.0.1 | 1.0.2 | manager.py |
| countdown | 1.0.0 | 1.0.1 | manager.py |
| f1-scoreboard | 1.2.2 | 1.2.3 | manager.py, scroll_display.py |
| football-scoreboard | 2.3.4 | 2.3.5 | football.py, manager.py, scroll_display.py, sports.py |
| hockey-scoreboard | 1.2.4 | 1.2.5 | base_classes.py, manager.py, scoreboard_renderer.py, scroll_display.py, sports.py |
| ledmatrix-flights | 1.0.0 | 1.0.1 | manager.py |
| ledmatrix-music | 1.0.4 | 1.0.5 | manager.py |
| ledmatrix-stocks | 2.0.2 | 2.0.3 | display_renderer.py (comment only) |
| ledmatrix-weather | 2.1.1 | 2.1.2 | manager.py |
| mqtt-notifications | 1.0.0 | 1.0.1 | manager.py |
| odds-ticker | 1.1.1 | 1.1.2 | manager.py, odds_renderer.py |
| soccer-scoreboard | 1.4.4 | 1.4.5 | manager.py, scroll_display.py, sports.py |
| static-image | 1.0.2 | 1.0.3 | manager.py |
| stock-news | 1.0.2 | 1.0.3 | manager.py |
| text-display | 1.0.1 | 1.0.2 | manager.py |
| ufc-scoreboard | 1.2.3 | 1.2.4 | manager.py, scroll_display.py, sports.py |
| web-ui-info | 1.0.0 | 1.0.1 | manager.py |
| youtube-stats | 1.0.0 | 1.0.1 | manager.py |

---

## Implementation Steps

### 1. Clone and apply fixes

```bash
git clone https://github.com/ChuckBuilds/ledmatrix-plugins /tmp/ledmatrix-plugins
cd /tmp/ledmatrix-plugins
git checkout -b fix/display-manager-width-height

# Mechanical replacement across all plugin Python files
find plugins -name "*.py" -exec sed -i \
  's/display_manager\.matrix\.width/display_manager.width/g; s/display_manager\.matrix\.height/display_manager.height/g' {} +

# Verify no references remain
grep -rn "display_manager\.matrix\.width\|display_manager\.matrix\.height" plugins/ --include="*.py"
# Expected: no output (comment in ledmatrix-stocks is also fixed, which is fine)
```

### 2. Bump manifest versions (patch)

```python
import json, os

plugins_dir = 'plugins'
for plugin in os.listdir(plugins_dir):
    manifest_path = os.path.join(plugins_dir, plugin, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        # Check if this plugin had changes
        # Only bump if changed — use git diff to check
        parts = manifest['version'].split('.')
        parts[2] = str(int(parts[2]) + 1)
        manifest['version'] = '.'.join(parts)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            f.write('\n')
```

### 3. Regenerate registry

```bash
python update_registry.py
```

### 4. Commit and open PR

```bash
git add -A
git commit -m "fix: replace display_manager.matrix.width/height with display_manager.width/height"
git push origin fix/display-manager-width-height
gh pr create --title "fix: use DisplayManager width/height properties" \
  --body "Replace direct matrix object access with safe DisplayManager properties across all 20 affected plugins."
```

---

## Notes

- The `display_manager.width` / `.height` properties (in `src/display_manager.py` of LEDMatrix core) handle fallback logic for real hardware, emulator mode, and mocked test environments
- Some plugins had `hasattr` guards around the matrix access; after fixing, these guards become redundant but harmless
- The `ledmatrix-stocks` change is only in a code comment — included for consistency
