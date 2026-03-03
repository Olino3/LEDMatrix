# SPIKE-002 — Update Documentation for `uv` Migration

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike
**Depends on:** [FOUND-001](FOUND-001-pyproject-uv-migration.md)
**Blocks:** _(none)_

---

## Context

After FOUND-001, dependency management uses `pyproject.toml` + `uv.lock` instead of `requirements*.txt` files, and tool configuration (`pytest`, `mypy`) lives in `pyproject.toml` instead of standalone `.ini` files. Several documentation files still reference the old files and `pip install -r` commands.

---

## Affected Files

| File | References to Update |
|------|---------------------|
| `docs/HOW_TO_RUN_TESTS.md` | `pip install -r requirements.txt`, `pytest.ini` |
| `docs/EMULATOR_SETUP_GUIDE.md` | `pip install -r requirements-emulator.txt`, `pip install -r requirements.txt` |
| `docs/TROUBLESHOOTING.md` | `pip install -r requirements.txt`, `pip install -r web_interface/requirements.txt` |
| `docs/DEVELOPER_QUICK_REFERENCE.md` | `requirements.txt` in troubleshooting table |
| `web_interface/README.md` | `requirements.txt` in directory tree listing |
| `docs/archive/*` | Various references (lower priority — historical context) |

---

## Acceptance Criteria

- [ ] All active (non-archive) docs reference `uv sync` instead of `pip install -r requirements.txt`
- [ ] Emulator setup guide uses `uv sync --extra emulator` instead of `pip install -r requirements-emulator.txt`
- [ ] Test docs reference `uv run pytest` and note that config is in `pyproject.toml` (not `pytest.ini`)
- [ ] Any `pip install` commands for dev/test are replaced with `uv sync --extra dev --extra test`
- [ ] Directory tree listings in docs are updated to show `pyproject.toml` and `uv.lock` instead of `requirements*.txt`
- [ ] Archive docs are left as-is (they document historical state)

---

## Notes

- `CLAUDE.md` should also be reviewed but may be updated separately as part of ongoing maintenance.
- Keep the documentation changes minimal — replace the specific commands, don't rewrite entire sections.
