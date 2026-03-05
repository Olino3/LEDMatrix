# Commit Conventions

## Format

```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Rules

- **One logical unit of work per commit.** If you can describe it with "and", split it into two commits.
- **RED before GREEN:** Failing tests must be committed before implementation.
  - RED test commits use type `test`
  - GREEN implementation commits use `feat` or `fix`
- Squash-and-merge preferred for PRs into `main`; `main` is protected — all changes via PR.
- Branch naming: `feature/`, `fix/`, `hotfix/`, `refactor/` + kebab-case description.

## Examples

```
test(config): add failing tests for ConfigValidator class
feat(config): implement ConfigValidator to pass RED tests
fix(display): correct matrix height calculation for 16x32 panels
chore(deps): bump manifest version for transit-board plugin
```
