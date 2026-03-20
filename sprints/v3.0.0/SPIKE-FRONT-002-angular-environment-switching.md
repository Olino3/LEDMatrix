# SPIKE-FRONT-002 — Angular Environment File Switching

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

Angular 17+ changed how environment file replacement works. The legacy `fileReplacements` in `angular.json` is deprecated in favor of build-time approaches. FRONT-001 created `environment.ts` and `environment.prod.ts`, but the switching mechanism is not yet wired.

FRONT-003 (API service layer) will need to use `environment.apiBase` — this spike ensures the pattern is documented before that work begins.

## Questions to Investigate

- What is the Angular 21 recommended way to switch environment files between dev and prod builds?
- Is `fileReplacements` still supported in Angular 21, or fully removed?
- Should we use `APP_INITIALIZER`, `provideAppConfig()`, or another pattern?
- How do `ng build` vs `ng build --configuration production` select the right environment?

## Acceptance Criteria

- [ ] Document the correct environment switching pattern for Angular 21
- [ ] Wire `environment.ts` → `environment.prod.ts` switching in `angular.json` if needed
- [ ] Verify `ng build` (dev) and `ng build --configuration production` use correct environments
