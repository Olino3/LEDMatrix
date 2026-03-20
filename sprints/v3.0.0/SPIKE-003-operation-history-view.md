# SPIKE-003 — Operation History View

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-007](FRONT-007-logs-store-modules.md)
**Blocks:** _(none)_

---

## Context

The HTMX frontend had an "Operation History" partial (`web_interface/templates/v3/partials/operation_history.html`) that shows recent plugin store operations (install, update, uninstall) with timestamps and status. This provides useful feedback for debugging store issues.

---

## Acceptance Criteria

- [ ] Operation history is accessible from the Store page (as a tab or expandable section)
- [ ] Shows recent store operations: type (install/update/uninstall), plugin name, timestamp, status (success/failed)
- [ ] Operations listed in reverse chronological order
- [ ] Clear history button

---

## Implementation Checklist

### 1. Create operation history component

- [ ] Create `frontend/src/app/features/store/operation-history/operation-history.component.ts`
- [ ] Fetch history from backend (if an endpoint exists) or maintain client-side history
- [ ] Display in PrimeNG `Timeline` or `Table`
- [ ] Color-code by status: green for success, red for failure

### 2. Integrate with store module

- [ ] Add as a tab or expandable panel in the Store page
- [ ] Update history whenever an install/update/uninstall completes

### 3. Commit

```bash
git add frontend/src/app/features/store/operation-history/
git commit -m "feat(frontend): add plugin operation history view to store"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Component exists
test -f frontend/src/app/features/store/operation-history/operation-history.component.ts && echo "OK: operation history"

# 2. Build succeeds
cd frontend && npx ng build && echo "OK: build with operation history"
```

---

## Notes

- The backend may or may not have a dedicated operation history endpoint. Check `src/api/routers/store.py` for available endpoints. If none exists, maintain history client-side in `SessionStorage` (lost on page refresh, which is acceptable for now).
- This is a nice-to-have feature. If it adds significant complexity, it can be deferred to Phase 5.
