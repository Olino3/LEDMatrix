# SPIKE-FRONT-002 — Angular Environment File Switching

**Status:** Done
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

Angular 17+ changed how environment file replacement works. The legacy `fileReplacements` in `angular.json` is deprecated in favor of build-time approaches. FRONT-001 created `environment.ts` and `environment.prod.ts`, but the switching mechanism was not wired.

## Findings

### `fileReplacements` is still supported in Angular 21

Despite being considered legacy, `fileReplacements` in `angular.json` is fully supported in Angular 21 with the `@angular/build:application` builder. It remains the simplest and most widely documented approach for environment switching.

### How it works

In `angular.json`, the `production` configuration includes:

```json
"fileReplacements": [
  {
    "replace": "src/environments/environment.ts",
    "with": "src/environments/environment.prod.ts"
  }
]
```

- `ng build` (default config: production) → uses `environment.prod.ts`
- `ng build --configuration development` → uses `environment.ts`
- `ng serve` (default config: development) → uses `environment.ts`

Code always imports from `environments/environment` — the build system swaps the file at compile time.

### Alternative approaches considered

| Approach | Verdict |
|----------|---------|
| `fileReplacements` | **Chosen** — simple, well-supported, works with Angular 21 |
| `APP_INITIALIZER` + runtime config | Overkill — adds HTTP call at startup, environment is static |
| `provideAppConfig()` | Not a standard Angular API for this purpose |
| Build-time `define` replacements | Requires custom webpack/esbuild config — unnecessary complexity |

## Changes Made

- Added `fileReplacements` to `frontend/angular.json` under `configurations.production`
- Verified `ng build` (production) and `ng build --configuration development` both succeed

## Acceptance Criteria

- [x] Document the correct environment switching pattern for Angular 21 → **`fileReplacements` in angular.json**
- [x] Wire `environment.ts` → `environment.prod.ts` switching in `angular.json` → **Done**
- [x] Verify `ng build` (dev) and `ng build --configuration production` use correct environments → **Both build successfully**
