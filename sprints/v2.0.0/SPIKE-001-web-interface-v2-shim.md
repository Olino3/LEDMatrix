# SPIKE-001 — Compatibility Shim for `web_interface_v2` Import

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-008](BACK-008-flask-removal-cleanup.md)
**Blocks:** _(none -- end of chain)_

---

## Context

Four plugins import `from web_interface_v2 import increment_api_counter`:
- `ledmatrix-music`
- `ledmatrix-weather`
- `odds-ticker`
- `youtube-stats`

Additionally, `src/base_odds_manager.py` imports `increment_api_counter` from `web_interface_v2` with a fallback no-op.

The `web_interface_v2.py` file no longer exists in the repo (it was a legacy module), but the import path is used by plugins in the monorepo. Per the migration conventions (`.claude/rules/migration.md`), when removing a module, a compatibility shim must be maintained at the original import path for one full release cycle, with a deprecation warning.

---

## Acceptance Criteria

- [ ] `web_interface_v2.py` exists at repo root as a compatibility shim
- [ ] Shim re-exports `increment_api_counter` pointing to the new FastAPI-backed counter
- [ ] Shim emits `DeprecationWarning` once per session on first import
- [ ] `src/api/services/api_counter.py` implements the new counter service
- [ ] `src/base_odds_manager.py` updated to import from new path (with fallback preserved)
- [ ] `SHIMS.md` created at repo root documenting this shim and its removal phase (Phase 9)
- [ ] Plugin impact documented: 4 plugins + `base_odds_manager.py`

---

## Implementation Checklist

### 1. Create new counter service

- [ ] Create `src/api/services/__init__.py`
- [ ] Create `src/api/services/api_counter.py` with `increment_api_counter(kind: str, count: int = 1)` function
- [ ] Counter should store counts in memory (simple dict) -- no persistence needed
- [ ] Add `get_api_counts() -> dict[str, int]` for the system status endpoint

### 2. Create compatibility shim

- [ ] Create `web_interface_v2.py` at repo root
- [ ] Import and re-export `increment_api_counter` from `src.api.services.api_counter`
- [ ] Emit `warnings.warn("Importing from web_interface_v2 is deprecated. Use src.api.services.api_counter instead. This shim will be removed in v6.2.0.", DeprecationWarning, stacklevel=2)` on module import
- [ ] Use `_warned` flag to emit only once per session

### 3. Update internal consumer

- [ ] Update `src/base_odds_manager.py` to import from `src.api.services.api_counter` instead of `web_interface_v2`
- [ ] Keep the fallback no-op pattern for environments where the API is not running

### 4. Create `SHIMS.md`

- [ ] Create `SHIMS.md` at repo root
- [ ] Document the `web_interface_v2.increment_api_counter` shim
- [ ] Include: original path, new path, affected consumers, removal phase (v6.2.0 / Phase 9)

### 5. Tests

- [ ] Test that `from web_interface_v2 import increment_api_counter` works
- [ ] Test that importing the shim emits a `DeprecationWarning`
- [ ] Test that `increment_api_counter` increments the counter
- [ ] Test that `src.api.services.api_counter` works directly

### 6. Commit

```bash
git add web_interface_v2.py src/api/services/ src/base_odds_manager.py SHIMS.md
git commit -m "feat(api): add web_interface_v2 compatibility shim for plugin migration"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Shim exists
test -f web_interface_v2.py && echo "OK: shim exists"

# 2. Import works and warns
python3 -W all -c "
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    from web_interface_v2 import increment_api_counter
    assert len(w) == 1, f'Expected 1 warning, got {len(w)}'
    assert issubclass(w[0].category, DeprecationWarning)
    print('OK: shim imports and warns')
"

# 3. New counter works
python3 -c "
from src.api.services.api_counter import increment_api_counter, get_api_counts
increment_api_counter('test', 5)
counts = get_api_counts()
assert counts.get('test') == 5, f'Expected 5, got {counts.get(\"test\")}'
print('OK: counter works')
"

# 4. SHIMS.md exists
test -f SHIMS.md && echo "OK: SHIMS.md exists"
grep -q "web_interface_v2" SHIMS.md && echo "OK: shim documented"

# 5. base_odds_manager updated
grep -q "src.api.services.api_counter" src/base_odds_manager.py && echo "OK: base_odds_manager updated"
```

---

## Notes

- The 4 affected plugins (`ledmatrix-music`, `ledmatrix-weather`, `odds-ticker`, `youtube-stats`) are NOT updated in this ticket. They continue to use the shim. Plugin updates happen in Phase 9 (v6.2.0).
- The shim is intentionally minimal -- just a re-export with a deprecation warning.
- `SHIMS.md` will accumulate entries across phases as more shims are added (Phase 6, Phase 7). Each entry should include: original path, new path, consumers, and removal phase.
- Plugin Impact: 4 plugins in `ledmatrix-plugins` monorepo will see the deprecation warning in logs but continue to function.
