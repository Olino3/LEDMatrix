# SPIKE-004 — Remove Deprecated Legacy Shell Scripts

**Status:** Open
**Phase:** v1.1.0 — Foundation
**Type:** Spike / Cleanup
**Depends on:** [FOUND-003](FOUND-003-matrix-cli-install-doctor.md)
**Blocks:** _(none)_

---

## Context

FOUND-003 added deprecation warnings to `start_display.sh`, `stop_display.sh`, and `web_interface/run.sh`, directing users to the `matrix` CLI equivalents (`matrix service start`, `matrix service stop`, `matrix web`). These scripts should be removed after sufficient notice period.

Additionally, `first_time_install.sh` contains dead code (lines 634-729 and 768-778) that references the now-deleted `requirements.txt` / `web_interface/requirements.txt` files. The `[ -f ... ]` guards cause these sections to skip gracefully, but the code is misleading and should be cleaned up or the entire script replaced by `matrix install`.

---

## Acceptance Criteria

- [ ] `start_display.sh` removed from repo root
- [ ] `stop_display.sh` removed from repo root
- [ ] `web_interface/run.sh` removed
- [ ] `first_time_install.sh` dead code cleaned up (or entire script replaced by `matrix install` documentation)
- [ ] Any references to removed scripts in docs are updated
- [ ] `CLAUDE.md` updated if it references these scripts

---

## Notes

- Ensure no systemd service files or CI scripts reference the removed shell scripts before deleting.
- Consider keeping `first_time_install.sh` as a thin wrapper that calls `matrix install` for backwards compatibility, or remove it entirely with a note in the release changelog.
