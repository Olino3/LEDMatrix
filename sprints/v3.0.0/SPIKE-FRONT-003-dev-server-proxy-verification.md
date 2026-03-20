# SPIKE-FRONT-003 — Dev Server Proxy Verification

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

FRONT-001 created `proxy.conf.json` to route `/api/v3` and `/stream` from Angular dev server (port 4200) to FastAPI (port 5000). This cannot be fully verified without both servers running simultaneously.

## Questions to Investigate

- How to run both Angular dev server and FastAPI simultaneously for development?
- Should we add a `Makefile` target, npm script, or `concurrently` package?
- What's the developer workflow: two terminals, or single command?
- Does the SSE `/stream` proxy work correctly with keep-alive connections?

## Acceptance Criteria

- [ ] Document the dev workflow for running Angular + FastAPI together
- [ ] Add a convenience command (Makefile target, npm script, or shell script)
- [ ] Manually verify proxy routes `/api/v3/*` and `/stream/*` forward correctly
- [ ] Verify SSE streams work through the proxy
