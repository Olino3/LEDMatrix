# SPIKE-FRONT-001 — Node.js in Distrobox

**Status:** Done
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Spike
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)

---

## Context

The distrobox (`debian-trixie`) may not have Node.js installed. Angular development commands (`ng serve`, `ng build`, `ng test`, `ng lint`) require Node.js 18+. Currently, FRONT-001 ran Angular CLI on the host (Node.js v24.14.0), but downstream tickets (FRONT-002+) need a consistent dev environment.

## Findings

### Node.js is available in both host and distrobox

Node.js v24.14.0 and npm v11.9.0 are available in both environments via NVM (`~/.nvm/`). The NVM installation is in the user's home directory, which is shared between host and distrobox, so the same Node.js version is available everywhere.

| Environment | Node.js | npm | Angular CLI | Source |
|-------------|---------|-----|-------------|--------|
| Host (Fedora) | v24.14.0 | v11.9.0 | v21.2.3 | `~/.nvm/` |
| Distrobox (debian-trixie) | v24.14.0 | v11.9.0 | v21.2.3 | `~/.nvm/` (shared) |

### Recommendation: Run Angular commands on the host

Angular commands (`ng build`, `ng serve`, `ng test`, `ng lint`) do **not** require distrobox — they have no C compilation dependencies or Python venv requirements. Running on the host is simpler and avoids the ephemeral venv issue.

The distrobox is only needed for Python commands (pytest, mypy, uv sync).

### CI/CD

GitHub Actions should install Node.js 18+ via `actions/setup-node@v4`. This is independent of the local distrobox setup.

## Changes Made

- Updated `.claude/CLAUDE.md` — added Node.js/Angular CLI section under dev environment, Angular commands to "do NOT need distrobox" list, and Angular frontend dev commands

## Acceptance Criteria

- [x] Document whether Angular commands should run on host or distrobox → **Host** (no distrobox needed)
- [x] If distrobox: install Node.js 18+ and verify `ng build` works inside it → **Already available** via shared NVM
- [x] Update `CLAUDE.md` with Angular dev command conventions → **Done**
