# Architecture Guardrails

Applies to: `src/**/*`

## Display Dimensions

- ALWAYS use `display_manager.width` / `display_manager.height`
- NEVER use `display_manager.matrix.width` / `display_manager.matrix.height`

## Logging

- ALWAYS use `get_logger()` from `src.logging_config`
- NEVER use `logging.getLogger()` directly

## DisplayManager

- `DisplayManager` is a singleton — do not create new instances
- Use the instance passed to plugins via `self.display_manager`

## Config System

- Plugin config is delivered as a plain `dict` — do not convert to Pydantic models (that is Phase 2 work)
- `ConfigManager`, `ConfigService`, and `ConfigManagerAtomic` coexist until Phase 7 — do not remove any of them

## Background Services

- Do not hardcode `max_workers`, `timeout`, or `retry` values — read from config

## Stable Import Paths (do not change until noted phase)

| Import path | Stable until |
|---|---|
| `src.plugin_system.base_plugin.VegasDisplayMode` | Phase 6 |
| `src.background_data_service.get_background_service` | Phase 6 |
| `src.base_odds_manager.BaseOddsManager` | Phase 6 |
| `src.common.scroll_helper.ScrollHelper` | Phase 7 |
| `src.common.logo_helper.LogoHelper` | Phase 7 |

## ROADMAP Phase Notes

- **Phase 2 (v2.0.0):** Flask → FastAPI migration. Do not deepen Flask coupling or add new Jinja2 templates.
- **Phase 3 (v3.0.0):** HTMX → Angular + PrimeNG. No new HTMX-only UI patterns.
- **Phase 6 (v5.0.0):** Plugin system DI refactor — `StoreManager` will be decomposed.
- **Phase 7 (v6.0.0):** Core architecture refactor — God class decomposition, state machines.

See `.claude/rules/roadmap.md` for the full phase plan.

## Violation Baselines (do not increase)

Before committing changes to `src/`, verify these counts have not increased:

| Violation | Baseline | Check command |
|---|---|---|
| `logging.getLogger` usage | 36 files | `grep -rl "logging\.getLogger" src/ \| wc -l` |
| `.matrix.width` / `.matrix.height` | 0 in src/ | `grep -rn "\.matrix\.\(width\|height\)" src/` |
| New `DisplayManager()` instantiation | 0 | `grep -rn "DisplayManager()" src/ \| grep -v "# singleton"` |

New code MUST use `get_logger()` and `display_manager.width`/`.height`. Do not add to existing violations.
