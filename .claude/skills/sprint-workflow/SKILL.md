---
name: sprint-workflow
description: End-to-end sprint workflow connecting PM agent, TDD cycle, and BA agent for any ROADMAP phase
user-invocable: true
---

# Sprint Workflow

Guides you through the complete sprint lifecycle for any ROADMAP phase, connecting the PM agent, RED/GREEN TDD agents, and BA agent into a cohesive workflow.

## Arguments

- `version` (required) — target phase version (e.g., `v2.0.0`)

## Procedure

### Phase 1: Sprint Planning

1. Create a feature branch: `git checkout -b feature/phase-<N>-<theme>` from `develop`
2. Invoke the PM agent to generate the sprint directory and tickets:
   ```
   @pm-agent <version>
   ```
3. Review the generated `sprints/<version>/README.md` — verify ticket count, dependency graph, and Definition of Done
4. Commit the sprint directory: `git add sprints/<version>/ && git commit -m "chore(sprint): generate <version> sprint tickets"`

### Phase 2: Ticket Execution

For each ticket in dependency order (check the dependency graph in `sprints/<version>/README.md`):

1. **Read the ticket** — understand acceptance criteria and implementation checklist
2. **RED step** — invoke the red agent or manually write failing tests:
   ```
   @red-agent <ticket description / spec>
   ```
3. **Commit RED** — `test(scope): add failing tests for <feature>`
4. **GREEN step** — invoke the green agent or implement the minimum code:
   ```
   @green-agent
   ```
5. **Commit GREEN** — `feat(scope): implement <feature> to pass RED tests`
6. **REFACTOR** (if needed) — clean up, ensure tests still pass
7. **Update ticket status** — change `Status: Open` to `Status: Done` in the ticket file
8. **Repeat** for the next ticket

### Phase 3: Sprint Verification

1. Run the full test suite:
   ```bash
   EMULATOR=true uv run pytest test/ -q --override-ini="addopts=" --ignore=test/plugins
   ```
2. Run type checking:
   ```bash
   uv run mypy src/ --ignore-missing-imports
   ```
3. Run linting:
   ```bash
   uv run ruff check src/
   ```
4. Invoke the BA agent to verify all completed tickets and produce the health report:
   ```
   @ba-agent <version>
   ```
5. Address any BA recommendations (failed verifications, gaps, dependency issues)

### Phase 4: Iteration

If the BA report identifies issues:

1. Fix failing verifications — update code, re-run tests
2. Close gaps — create new tickets if needed, implement them via RED/GREEN
3. Re-run `@ba-agent <version>` until all tickets pass verification
4. Ensure sprint README is up to date (BA agent does this automatically)

### Phase 5: Sprint Close

1. Final commit with all ticket statuses updated
2. Push branch and create PR to `main`:
   ```bash
   git push -u origin feature/phase-<N>-<theme>
   gh pr create --title "Phase <N>: <theme>" --body "Sprint summary..."
   ```
3. Squash and merge after review

## Key Rules

- **TDD is mandatory** — every ticket follows RED → GREEN → REFACTOR
- **One logical unit per commit** — RED and GREEN are separate commits
- **Dependency order matters** — don't start a ticket until its dependencies are Done
- **Tests must pass at every commit** — never commit broken tests (except RED commits where the NEW tests fail)

## References

- `.claude/agents/pm-agent.md` — sprint planning agent
- `.claude/agents/ba-agent.md` — sprint verification agent
- `.claude/agents/red-agent.md` — failing test generator
- `.claude/agents/green-agent.md` — minimum implementation agent
- `.claude/rules/tdd.md` — TDD enforcement rules
- `.claude/rules/commits.md` — commit conventions
- `ROADMAP.md` — phase details and acceptance criteria
