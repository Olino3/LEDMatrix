---
name: arch-audit
description: Run architecture violation baseline checks and God class metrics for LEDMatrix src/ modules
user-invocable: true
---

# Architecture Audit

Quick architecture health check that verifies violation baselines from `.claude/rules/architecture.md` and reports God class metrics.

## Arguments

- `module` (optional) — specific file or directory to audit (default: `src/`)

## Procedure

### 1. Check violation baselines

Run these checks and compare against documented baselines:

| Violation | Baseline | Command |
|---|---|---|
| `logging.getLogger` usage | 36 files | `grep -rl "logging\.getLogger" src/ \| wc -l` |
| `.matrix.width` / `.matrix.height` | 0 in src/ | `grep -rn "\.matrix\.\(width\|height\)" src/` |
| New `DisplayManager()` instantiation | 0 | `grep -rn "DisplayManager()" src/ \| grep -v "# singleton"` |

Report PASS if at or below baseline, FAIL if above.

### 2. God class metrics

For each known God class, measure:
- `src/display_controller.py` (Phase 7 target)
- `src/plugin_system/store_manager.py` (Phase 6 target)

Metrics per file:
- Total LOC: `wc -l <file>`
- Method count: `grep -c "def " <file>`
- Class count: `grep -c "^class " <file>`

### 3. Large file scan

Find any files exceeding 500 LOC threshold:
```bash
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -20
```

Flag files > 500 LOC as WARN.

### 4. If a specific module was provided

Run the full arch-validator-agent metrics on that module:
- LOC, class count, method count, fan-out, fan-in
- Apply thresholds from `.claude/rules/architecture.md`

### 5. Generate report

```
Architecture Audit Report
=========================
Date: <date>
Scope: <module or src/>

## Violation Baselines
| Violation | Baseline | Current | Status |
|---|---|---|---|
| logging.getLogger files | 36 | <N> | PASS/FAIL |
| .matrix.width/height | 0 | <N> | PASS/FAIL |
| DisplayManager() instantiation | 0 | <N> | PASS/FAIL |

## God Classes
| Class | File | LOC | Methods | Decomposition Phase |
|---|---|---|---|---|
| DisplayController | src/display_controller.py | <N> | <N> | Phase 7 (v6.0.0) |
| StoreManager | src/plugin_system/store_manager.py | <N> | <N> | Phase 6 (v5.0.0) |

## Large Files (> 500 LOC)
| File | LOC | Status |
|---|---|---|
| <file> | <N> | WARN |

## Verdict: PASS / WARN / FAIL
```

## References

- `.claude/rules/architecture.md` — violation baselines and thresholds
- `.claude/rules/roadmap.md` — decomposition phase schedule
- `.claude/agents/arch-validator-agent.md` — detailed complexity analysis agent
