# SPIKE-006 — FastAPI Rate Limiting via slowapi

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Spike
**Depends on:** [BACK-004](BACK-004-middleware-stack.md), [BACK-007](BACK-007-sse-migration.md)

---

## Context

The Flask app uses `flask-limiter` for basic rate limiting (1000 req/min default, 20/min on SSE endpoints). The BACK-004 ticket originally called for `slowapi` (the FastAPI-compatible equivalent), but this was deferred because:

1. It introduces a new dependency (`slowapi`) that wraps the same `limits` library
2. The current rate limiting is purely defensive ("prevent accidental abuse"), not security-critical
3. SSE endpoints (BACK-007) need to be migrated first before rate limits can be applied to them

## Scope

- [x] Add `slowapi>=0.1.9` to `pyproject.toml`
- [x] Create `src/api/middleware/rate_limit.py` with default 1000/min limit
- [x] Apply 20/min limit to SSE streaming endpoints
- [x] Wire into `register_middleware()` (SlowAPIMiddleware + 429 handler)
- [x] Tests for rate limit setup, SSE limits, and 429 handler (8 tests)

## Notes

- `flask-limiter` will be removed in BACK-008 alongside Flask itself
- Both `flask-limiter` and `slowapi` use `limits` under the hood, so storage config is identical
