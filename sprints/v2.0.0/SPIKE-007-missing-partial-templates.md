# SPIKE-007 — Create Missing Partial Templates (weather, stocks)

> **For Claude:** Use `superpowers:writing-plans` before touching any files.

**Status:** Open
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [SPIKE-002](SPIKE-002-pages-v3-transition.md)
**Blocks:** _(none)_

---

## Context

The Flask blueprint `pages_v3.py` referenced `v3/partials/weather.html` and `v3/partials/stocks.html` templates, but these files were never created. Both partials returned 500 errors in the Flask version and continue to do so in the FastAPI port (SPIKE-002).

The pages router (`src/api/routers/pages.py`) maps `weather` and `stocks` as simple partials that pass `main_config` — but the template files don't exist.

---

## Acceptance Criteria

- [ ] `web_interface/templates/v3/partials/weather.html` exists with a functional config form
- [ ] `web_interface/templates/v3/partials/stocks.html` exists with a functional config form
- [ ] Both partials render without errors via `GET /v3/partials/weather` and `GET /v3/partials/stocks`
- [ ] Tests added for both partials

---

## Notes

- These should follow the same pattern as `general.html` or `display.html` — reading from `main_config.weather` and `main_config.stocks` respectively.
- The config schema for weather/stocks fields should be checked against `config/config.template.json`.
- This is a UI gap, not a backend issue — the API routes work correctly.
