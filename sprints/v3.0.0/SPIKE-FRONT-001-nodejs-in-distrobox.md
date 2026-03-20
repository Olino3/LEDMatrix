# SPIKE-FRONT-001 — Node.js in Distrobox

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

The distrobox (`debian-trixie`) may not have Node.js installed. Angular development commands (`ng serve`, `ng build`, `ng test`, `ng lint`) require Node.js 18+. Currently, FRONT-001 ran Angular CLI on the host (Node.js v24.14.0), but downstream tickets (FRONT-002+) need a consistent dev environment.

## Questions to Investigate

- Is Node.js available in the distrobox? If so, what version?
- Should Angular commands run on the host or inside the distrobox?
- If in the distrobox, how to install Node.js 18+ (apt, nvm, fnm)?
- How does this interact with CI/CD (GitHub Actions)?
- Should `CLAUDE.md` be updated with Angular-specific dev commands?

## Acceptance Criteria

- [ ] Document whether Angular commands should run on host or distrobox
- [ ] If distrobox: install Node.js 18+ and verify `ng build` works inside it
- [ ] Update `CLAUDE.md` with Angular dev command conventions
