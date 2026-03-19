# ROADMAP Awareness

This project has a structured multi-phase roadmap. When writing code, avoid deepening tech debt in areas scheduled for replacement.

## Phase Plan

| Phase | Version | Theme | Avoid deepening |
|---|---|---|---|
| **1 (current)** | v1.1.0 | `uv` + `pyproject.toml`, `matrix` CLI, CI setup | — |
| **2** | v2.0.0 | Flask → FastAPI | New Flask routes, Jinja2 templates |
| **3** | v3.0.0 | HTMX → Angular + PrimeNG | New HTMX-only UI patterns |
| **4** | v4.0.0 | Docker-first deployment | Bare-metal-only install assumptions |
| **5** | v4.1.0 | Structured logging, health endpoints, error handling | Ad-hoc logging patterns |
| **6** | v5.0.0 | Plugin system DI, `StoreManager` decomposition | Tight plugin coupling |
| **7** | v6.0.0 | Core architecture refactor, God class decomposition | Expanding `DisplayController` |
| **8** | v6.1.0 | 70%+ test coverage, dead code removal | Untested surface area |
| **9** | v6.2.0 | Plugin ecosystem migration, shim removal | Shim patterns |

## Stable Import Paths

See `.claude/rules/architecture.md` for the list of import paths that must not change until their noted phase.

## Current Phase Work (Phase 1)

- `uv` + `pyproject.toml` migration complete
- `matrix` CLI at `scripts/matrix_cli.py` (installed via `make install-matrix`)
- CI pipeline setup in progress
- Focus: stabilize tooling, do not introduce new features that expand scope
