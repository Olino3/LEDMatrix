# Migration Conventions

Applies to: Any phase involving API migration, framework swap, or module decomposition (Phases 2, 3, 6, 7, 9).

## Compatibility Shims

- When moving an import path, ALWAYS maintain a re-export at the original path for one full release cycle
- Re-exports must include a deprecation warning logged once per session via `warnings.warn(..., DeprecationWarning)`
- Document the shim in ROADMAP.md under the relevant phase's "Plugin Impact" section
- Track all active shims in a `SHIMS.md` file at repo root

## Migration Order

1. Write failing tests for the NEW interface (RED)
2. Implement the new module/endpoint (GREEN)
3. Add compatibility shim at the old path
4. Update internal consumers to use new path
5. Document shim in SHIMS.md with removal phase
6. Plugin consumers updated in Phase 9 (or noted phase)

## Decomposition Rules (Phase 6/7)

- Original class becomes a thin orchestrator delegating to extracted classes
- Extracted classes define `Protocol` interfaces
- No extracted class exceeds 500 LOC
- Fan-out from orchestrator must not exceed 8 direct dependencies
- All extracted components must be independently unit-testable

## Plugin Impact Checklist

For any change that affects plugin-visible APIs:

- [ ] Grep for all external consumers of the changing import path
- [ ] Count affected plugins (document in ticket)
- [ ] Create or update compatibility shim
- [ ] Add `minimum_core_version` to affected plugin manifests
- [ ] Run `python update_registry.py` for all affected plugins
