# LEDMatrix Roadmap

This document tracks planned improvements, features, and large-scale refactors for the LEDMatrix project.
Items are organized into versioned phases. Each phase delivers a cohesive set of changes before the next begins.

Current version: **v1.0.0**

---

## Phase 1 — Foundation `v1.1.0`

> Python modernization, developer tooling, and CI infrastructure. No breaking changes to public APIs or behavior.

### Package Management: `uv` + `pyproject.toml`
- Replace all `requirements.txt` files (root and `web_interface/`) with a single `pyproject.toml`
- Adopt `uv` as the package manager for dependency resolution, locking, and venv management
- Define optional dependency groups: `[dev]`, `[emulator]`, `[hardware]`, `[test]`
- Remove all `pip install` calls from scripts; route everything through `uv sync`
- Pin a `uv.lock` file for reproducible installs

### Virtual Environment First
- Ensure all runtime and install paths use the project venv — no system-wide package installs
- Update `matrix` CLI to bootstrap the venv automatically when missing
- Update systemd service files to activate the venv before launching

### `matrix` CLI Consolidation
- Absorb `first_time_install.sh` logic into `matrix install` / `matrix setup` subcommands
- Deprecate and remove standalone shell scripts (`first_time_install.sh`, `start_display.sh`, `stop_display.sh`, `run.sh`)
- `matrix` CLI becomes the single entry point for install, run, logs, and service management
- Add `matrix doctor` command: checks venv, dependencies, hardware, and service health

### CI Pipeline (GitHub Actions)
- **Lint & Format**: `ruff check` + `ruff format --check` on every push and PR
- **Type Check**: `mypy src/` gated on every PR
- **Tests**: `pytest` with coverage report uploaded as artifact; fail under 30% (raise threshold each phase)
- **Dependency Audit**: `uv pip audit` to flag known vulnerabilities
- Add pre-commit hooks mirroring CI checks (`ruff`, `mypy`)
- Matrix builds across Python 3.10, 3.11, 3.12

### Plugin Quick-Fixes (`ledmatrix-plugins`)
- Fix legacy `display_manager.matrix.width` / `.matrix.height` references in `football-scoreboard` and `hockey-scoreboard` — replace with the correct `display_manager.width` / `.height` properties
- Bump patch versions and run `update_registry.py` for both affected plugins
- No other plugins require changes at this phase

---

## Phase 2 — Backend Modernization `v2.0.0`

> Full Flask → FastAPI rewrite. Breaking change: API response formats and endpoint paths may change.

### FastAPI Migration
- Replace Flask and all blueprints with a FastAPI application (`src/api/`)
- Async-first: all I/O-bound route handlers use `async def`
- Auto-generated OpenAPI docs at `/docs` and `/redoc`
- Mount static files and legacy HTMX pages during transition (removed in Phase 3)
- Replace SSE streaming endpoints using `sse-starlette`
- Background jobs via FastAPI `BackgroundTasks` + `asyncio` (replace ad-hoc threading)

### Pydantic Settings & Config Management
- Replace `ConfigManager` / `ConfigService` / `ConfigManagerAtomic` three-tier confusion with a single unified `Config` class
- Use `pydantic-settings` for typed, validated configuration with env var overrides
- Define typed Pydantic models for all top-level config sections (system, plugin defaults, display, schedule)
- Plugin configs validated against their `config_schema.json` via Pydantic at load time, not at runtime
- Move secret management to a `SecretStore` abstraction (file-backed initially, extensible)
- Replace polling-based hot-reload with `watchdog` file system events
- Auto-clean config backups (retain last 5)

### Middleware & Auth
- CORS middleware for Angular frontend origin
- API key authentication middleware (configurable; off by default for local use)
- JWT support scaffolded for future multi-user scenarios
- Request ID middleware for correlation across logs

### Type Safety
- All FastAPI route handlers fully typed with Pydantic request/response models
- `mypy` `disallow_untyped_defs = True` enforced for `src/api/`

### Plugin Impact (`ledmatrix-plugins`)
- **`web_interface_v2` import breakage (4 plugins):** `ledmatrix-music`, `ledmatrix-weather`, `odds-ticker`, and `youtube-stats` all import `from web_interface_v2 import increment_api_counter`. When Flask is removed, this module disappears. Provide a compatibility shim at the same import path that routes to the new FastAPI-backed counter, or update all 4 plugins to use a new module path.
- **Config dict contract:** Plugins receive their config as a plain `dict` via `self.config`. Ensure the Pydantic Settings layer still delivers a plain dict to plugins (not a Pydantic model instance) to avoid breaking all 28 plugins without a coordinated update.
- Bump minor version and run `update_registry.py` for all 4 affected plugins.

---

## Phase 3 — Frontend Modernization `v3.0.0`

> Replace Jinja2/HTMX templates with a dedicated Angular + PrimeNG SPA. Breaking change: frontend is fully rebuilt.

### Angular SPA
- Angular 17+ application in `frontend/` directory
- PrimeNG component library for UI consistency and accessibility
- Angular CLI build pipeline integrated into the project (`ng build` outputs to `frontend/dist/`)
- FastAPI serves the built SPA from `/` and all API routes from `/api/v3/`

### Feature Modules (lazy-loaded)
- **Dashboard** — system status, active plugin, live display preview
- **Plugins** — browse, install, configure, enable/disable plugins
- **Settings** — system-wide config (display, schedule, brightness, network)
- **Logs** — live log stream viewer
- **Store** — plugin marketplace with search and one-click install

### Real-Time Updates
- Replace HTMX SSE polling with Angular `EventSource` service for log and stats streams
- WebSocket client for display preview stream

### Design System
- Dark-first theme using PrimeNG theming API
- Responsive layout (usable on phone/tablet for in-place configuration)
- Consistent loading, error, and empty states across all views

---

## Phase 4 — Containerization `v4.0.0`

> Docker-first deployment model. Runs as a privileged container on Pi for hardware access.

### Dockerfile
- Multi-stage build: Stage 1 builds Angular SPA; Stage 2 is the Python runtime
- Base image: `python:3.12-slim` with `uv` for dependency install
- Hardware layer (`rgbmatrix`) installed in the container; `/dev` devices mounted at runtime
- Emulator profile uses `RGBMatrixEmulator` instead — no hardware mounts needed

### Docker Compose
- `compose.yml` for full stack: display service + web/API service
- `compose.dev.yml` overlay: mounts source for live reload, enables emulator mode
- Named volumes for config, data, and font persistence
- Environment-driven config (Pydantic Settings reads from env)

### `matrix` CLI Docker Commands
- `matrix docker start` — pull and start containers
- `matrix docker stop` — stop containers
- `matrix docker logs` — tail container logs
- `matrix docker update` — pull latest image and restart
- `matrix docker build` — local image build for development

### Pi Deployment
- Container runs with `--privileged` and `/dev/mem`, `/dev/gpiomem` mounts
- `matrix install` detects Docker availability and offers container vs. native install
- Systemd unit files updated to manage Docker containers instead of bare processes

---

## Phase 5 — Observability `v4.1.0`

> Structured logging with correlation IDs, centralized error handling, and health monitoring. Additive — no breaking changes.

### Structured Logging
- All log output uses structured JSON format in production (`LEDMATRIX_JSON_LOGGING=true`)
- Request ID / correlation ID injected by FastAPI middleware, threaded through all log calls
- Plugin log entries include `plugin_id` field automatically
- Log rotation configured (size-based, keep 7 days)

### Centralized Error Handling
- FastAPI exception handler middleware catches and formats all unhandled exceptions
- Typed `ErrorContext` dataclass replaces free-form context dicts
- Consistent error response schema: `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`
- `ErrorAggregator` refactored to use dependency injection (no global singleton)

### Health & Metrics
- `/api/v3/health` — liveness check (returns 200 or 503)
- `/api/v3/health/ready` — readiness check (plugins loaded, display running)
- Plugin-level health metrics: last update time, error count, status
- Optional Sentry DSN config for error forwarding

### Silent Failure Elimination
- Audit and fix all locations where errors are silently swallowed
- Background fetch failures surface to health check, not just logs
- Plugin callback errors stored and visible in health endpoint

---

## Phase 6 — Plugin System Overhaul `v5.0.0`

> Major architectural refactor of the plugin subsystem. Breaking change for third-party plugins that depend on internal APIs.

### StoreManager Decomposition
- Split `StoreManager` (2,165 LOC) into focused classes:
  - `RegistryClient` — fetches and caches plugin registry from GitHub
  - `VersionResolver` — semantic version comparison and update detection
  - `PluginInstaller` — pip-based installation with retry and rollback
  - `PluginUpdater` — orchestrates update flow (backup → install → verify → activate)
- `StoreManager` becomes a thin orchestrator delegating to the above

### Dependency Injection & Interfaces
- Define `Protocol` interfaces for all major plugin system components:
  - `IPluginLoader`, `IPluginStateManager`, `ISchemaManager`, `IPluginExecutor`
- `PluginManager` depends on interfaces, not concrete classes
- All components injectable — enables full unit testing without filesystem or network

### Consolidated State Management
- Introduce `PluginStateSnapshot` dataclass: lifecycle state, enabled flag, last update time, error count
- `PluginStateManager` becomes the single source of truth (remove scattered dicts)
- State transitions validated and logged

### Dependency Installation Isolation
- Extract `PipDependencyInstaller` with retry logic, exponential backoff, and rollback on failure
- Separate dependency resolution from module loading

### Plugin Lifecycle Improvements
- Formal plugin dependency declarations (`manifest.json` `dependencies` field) for load ordering
- Lazy plugin initialization option (load on first display cycle, not at startup)
- Plugin sandboxing improvements: stricter timeout enforcement, resource limit monitoring

### Plugin Impact (`ledmatrix-plugins`)
- **`VegasDisplayMode` import (8 plugins):** `baseball-scoreboard`, `football-scoreboard`, `hockey-scoreboard`, `olympics`, `calendar`, `f1-scoreboard`, `soccer-scoreboard`, and `ufc-scoreboard` all import `VegasDisplayMode` from `src.plugin_system.base_plugin`. If the enum moves during the plugin system overhaul, maintain a re-export at the original path (`from src.plugin_system.base_plugin import VegasDisplayMode`) for one full release cycle before removing it.
- **`get_background_service` import (3 plugins):** `baseball-scoreboard`, `football-scoreboard`, and `hockey-scoreboard` import `from src.background_data_service import get_background_service`. If this module is renamed or restructured, provide a compatibility re-export.
- **`BaseOddsManager` import (3 plugins):** `baseball-scoreboard`, `football-scoreboard`, and `odds-ticker` import `from src.base_odds_manager import BaseOddsManager`. Maintain import path stability or update affected plugins.
- Add `minimum_core_version` field to `manifest.json` schema so the plugin system can warn when an installed plugin requires a newer core.

---

## Phase 7 — Core Architecture Refactor `v6.0.0`

> Decompose God classes, formalize state machines, and improve testability across the core runtime. Breaking change: internal APIs restructured.

### DisplayController Decomposition
- Extract `DisplayOrchestrator`: owns mode rotation, duration, scheduling, live priority arbitration
- Extract `ScheduleManager`: handles time-based on/off, brightness schedules
- Extract `OnDemandModeManager`: manages temporary display overrides and expiry
- `DisplayController` becomes a thin coordinator; individual concerns are independently testable

### Formal Display State Machine
- Introduce `DisplayState` enum: `INITIALIZING`, `NORMAL`, `LIVE_PRIORITY`, `ON_DEMAND`, `VEGAS`, `OFF`
- All state transitions logged with previous/next state and reason
- Invalid transitions raise explicit errors rather than silently falling through

### Vegas Mode State Machine
- Replace scattered boolean flags with `VegasState` enum: `IDLE`, `SCROLLING`, `PAUSED`, `STATIC_DISPLAYING`, `ERROR`
- `VegasStateManager` owns all transitions; saves and restores scroll position atomically
- Extract `InterruptChecker` for live priority and on-demand checks (decoupled from Vegas coordinator)
- `PluginVegasAdapter` simplified to a clean interface (SCROLL / FIXED_SEGMENT / STATIC modes)

### SportsCore Decomposition
- Replace monolithic `SportsCore` with focused mixins:
  - `LogoManagementMixin` — logo download, cache, fallback
  - `OddsDisplayMixin` — odds overlay rendering
  - `FontMixin` — adaptive font selection based on display dimensions
  - `BackgroundFetchMixin` — configurable background data service
- Introduce `DisplayDimensions` dataclass: centralizes `is_compact`, font size, logo size decisions
- Background service config driven by plugin config (not hardcoded `max_workers=1`)

### Utility Refactors
- `RenderContext` class: wraps `Image` + `ImageDraw` + display paste — decouples helpers from `DisplayManager`
- `LogoManager`: single source of truth for logo directory resolution, download, and caching
- `ResilientApiClient`: wraps `requests.Session` with circuit breaker (via `pybreaker`), retry, and exponential backoff
- Config-driven background service removes all hardcoded worker/timeout/retry values

### Config System Consolidation
- Merge `ConfigManager`, `ConfigService`, `ConfigManagerAtomic` into a single `Config` class
- `Config` composes a backend (`IConfigBackend`), watcher (`IConfigWatcher`), and atomic writer
- Replace polling-based file watcher with `watchdog`-based async events
- `SecretStore` abstraction with `FileSecretStore` and `EnvSecretStore` implementations

### Plugin Impact (`ledmatrix-plugins`)
- **`ScrollHelper` API (6 plugins):** `news`, `text-display`, `ledmatrix-stocks`, `ledmatrix-leaderboard`, `odds-ticker`, and one or more sports plugins use `ScrollHelper` from `src.common.scroll_helper`. Any `RenderContext` refactor that changes the `ScrollHelper` call signature must be backwards-compatible for one release, or all 6 plugins updated simultaneously.
- **`LogoHelper` → `LogoManager` rename (4 plugins):** `news` and sports plugins import `LogoHelper` from `src.common.logo_helper`. Maintain `LogoHelper` as a deprecated alias for `LogoManager` for one release cycle, then remove it.
- **`DisplayDimensions` dataclass (new):** No plugin changes required — plugins may optionally adopt the new dataclass but it is not forced at this phase.

---

## Phase 8 — Code Quality & Test Coverage `v6.1.0`

> Raise test coverage, eliminate remaining technical debt, and enforce quality standards. No breaking changes.

### Coverage Targets
| Module | Current (est.) | Target |
|---|---|---|
| Plugin system | ~40% | 80% |
| DisplayController | ~20% | 70% |
| Config system | ~35% | 75% |
| Vegas mode | <10% | 65% |
| Background services | ~0% | 70% |
| Web API | ~25% | 70% |
| Sports base classes | ~20% | 65% |
| **Overall** | **~25–35%** | **≥70%** |

### New Test Areas
- Plugin lifecycle integration: isolation, manifest validation, dependency rollback
- Display state machine: all valid and invalid transitions
- Config hot-reload: concurrent reads/writes, secret preservation, rapid file changes
- Vegas mode: static pause/resume, live priority interrupt, frame rate under load
- Background services: priority ordering, timeout handling, callback error propagation
- API endpoints: error cases, concurrent requests, SSE stream disconnect

### Linting & Formatting Enforcement
- `ruff` replaces `flake8`/`isort`; config in `pyproject.toml`
- `ruff format` replaces `black`
- `mypy` `disallow_untyped_defs = True` extended to all `src/` modules
- CI coverage gate raised to 70%

### Dead Code Removal
- Remove unimplemented priority queue in `BackgroundDataService` or fully implement it
- Remove unreachable config migration paths
- Audit and remove `# type: ignore` suppression comments; fix underlying issues

---

## Phase 9 — Plugin Ecosystem Migration `v6.2.0`

> Bring all 28 official plugins in `ledmatrix-plugins` fully in line with the new core APIs introduced in Phases 2, 6, and 7. Remove all compatibility shims. Breaking change for any third-party plugins built against the old internal APIs.

### Compatibility Shim Removal
- Remove the `web_interface_v2` compatibility shim introduced in Phase 2; update all 4 dependent plugins (`ledmatrix-music`, `ledmatrix-weather`, `odds-ticker`, `youtube-stats`) to use the new module path
- Remove deprecated `LogoHelper` alias; update 4 plugins to import `LogoManager` directly
- Remove deprecated `VegasDisplayMode` re-export shim; confirm all 8 plugins import from the new canonical path
- Remove deprecated `get_background_service` shim; update 3 sports plugins to new import
- Remove deprecated `BaseOddsManager` shim; update 3 affected plugins

### Manifest Schema Updates (all 28 plugins)
- Add `minimum_core_version` field to every `manifest.json` specifying the lowest core version the plugin is compatible with
- Add `api_version` field to declare which plugin contract version the plugin targets
- Run `update_registry.py` to push all updated manifests to `plugins.json`

### Config Schema Audit
- Validate all 28 `config_schema.json` files against the new Pydantic-based schema validation layer
- Fix any schemas that relied on undocumented leniency in the old `jsonschema` validator (e.g., missing `type`, implicit `additionalProperties: true`)
- Standardize required base fields across all schemas: `enabled`, `display_duration`, `transition`

### Plugin CI (`ledmatrix-plugins`)
- Add GitHub Actions workflow to the `ledmatrix-plugins` monorepo:
  - Install LEDMatrix core from the latest release tag
  - Run each plugin's `validate_config()` in emulator mode
  - Verify all 28 plugins load and call `update()` + `display()` without errors in emulator
- Pin tested core version in CI; bump when new core is released
- Add `matrix plugin health --all` integration test as a CI step

### `ScrollHelper` Adoption (6 plugins)
- Update `news`, `text-display`, `ledmatrix-stocks`, `ledmatrix-leaderboard`, `odds-ticker`, and any sports plugins using `ScrollHelper` to use the `RenderContext`-aware API introduced in Phase 7
- Remove any direct `display_manager.image.paste()` calls inside plugins; route through `RenderContext`

### `DisplayDimensions` Adoption (optional, recommended)
- Update sports plugins and any plugin with adaptive layout logic to use the new `DisplayDimensions` dataclass
- Replace inline `if self.display_height < 24:` guards with `dims.is_compact`
- Centralize font size selection via `dims.get_font_size(context)`

### Version Bumps & Registry Sync
- Bump minor version for all plugins receiving API-level changes; bump patch for manifest-only changes
- Run `update_registry.py` to produce a final `plugins.json` covering all 28 updated plugins
- Tag a `v6.2.0-compat` release in `ledmatrix-plugins` marking full compatibility with LEDMatrix v6.2.0

---

## Summary

| Phase | Version | Theme | Breaking | Plugins Affected |
|---|---|---|---|---|
| 1 | v1.1.0 | Foundation — `uv`, CI, `matrix` CLI | No | 2 (quick-fix) |
| 2 | v2.0.0 | Backend — FastAPI, Pydantic config | API | 4 (`web_interface_v2`) |
| 3 | v3.0.0 | Frontend — Angular + PrimeNG | Frontend | 0 |
| 4 | v4.0.0 | Docker — Privileged container, Compose | Deployment | 0 |
| 5 | v4.1.0 | Observability — Structured logs, health | No | 0 |
| 6 | v5.0.0 | Plugin System — DI, decomposition, interfaces | Internal | 14 (import paths) |
| 7 | v6.0.0 | Core Architecture — State machines, God class split | Internal | 10 (helpers) |
| 8 | v6.1.0 | Quality — Coverage 70%+, dead code, linting | No | 0 |
| 9 | v6.2.0 | Plugin Ecosystem Migration — shim removal, CI, manifests | Plugin API | 28 (all) |
