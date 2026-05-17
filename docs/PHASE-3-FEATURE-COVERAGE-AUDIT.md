# Phase 3 Feature Coverage Audit

**Task ID**: 2026-05-17-phase-d-feature-coverage-audit  
**Author**: Senior Engineer  
**Date**: 2026-05-17  
**Status**: Complete  
**Scope**: Phase 3 feature equalization across π.dev, Claude Code, Copilot CLI harnesses

---

## Executive Summary

Phase 3 delivered three monitoring features to the orchestration layer:

| Feature | Module | Status |
|---------|--------|--------|
| Token Tracking | `src/orchestration/monitoring/token_tracker.py` | ✅ Complete |
| Budget Checking | `src/orchestration/monitoring/budget_checker.py` | ✅ Complete |
| CLI Formatting | `src/orchestration/monitoring/cli_formatter.py` | ✅ Complete |

These features are **orchestration-layer concerns** — they track token usage and enforce budgets during agent execution. They are integrated into `orchestrator.py` and `invoke_agent.py`, which run in any harness that invokes the Python orchestration stack.

The three target harnesses (π.dev, Claude Code, Copilot CLI) are **renderer scripts** — they install configuration files into platform-specific directories. They do not execute the monitoring stack directly. Feature equalization therefore means:

1. **Consistent output formatting** — renderers should respect `NO_COLOR`, use ANSI colors consistently, and report timing/byte metrics.
2. **Consistent error handling** — all renderers should handle errors gracefully and clean up on failure.
3. **Consistent status reporting** — all renderers should have `--status` and `--uninstall` modes.
4. **Documentation** — each harness should document how to use the monitoring features when running the orchestrator within that harness.

---

## Feature Coverage Matrix

### Renderer-Layer Features

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI |
|---------|----------|-------------|-------|-------------|
| `--install` mode | ✅ | ✅ | ✅ | ✅ |
| `--uninstall` mode | ✅ | ✅ | ✅ | ✅ |
| `--status` mode | ✅ | ✅ | ✅ | ✅ |
| ANSI color output | ✅ | ❌ | ❌ | ✅ (stream mode) |
| `NO_COLOR` respect | ✅ (via TTY check) | ❌ | ❌ | ✅ |
| Per-item timing | ✅ | ❌ | ❌ | ✅ (stream mode) |
| Byte-count reporting | ✅ | ❌ | ❌ | ✅ (stream mode) |
| Streaming JSON output | ❌ | ❌ | ❌ | ✅ (`--stream=json`) |
| Marker-based tracking | ✅ | ✅ | ✅ | ✅ |
| Foreign file protection | ✅ | ✅ | ✅ | ✅ |
| Explicit argparse | N/A (bash) | N/A (bash) | ✅ | N/A (bash) |
| Error handling | ✅ | ✅ | ✅ | ✅ |
| Git hooks install | ✅ | ❌ | ❌ | ✅ |

### Orchestration-Layer Features (available in all harnesses via Python stack)

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI |
|---------|----------|-------------|-------|-------------|
| TokenTracker | ✅ | ✅ | ✅ | ✅ |
| BudgetChecker | ✅ | ✅ | ✅ | ✅ |
| CLIFormatter | ✅ | ✅ | ✅ | ✅ |
| OrchestratorCLI | ✅ | ✅ | ✅ | ✅ |
| Prometheus metrics | ✅ | ✅ | ✅ | ✅ |

**Note**: All orchestration-layer features are available in all harnesses because they live in `src/orchestration/monitoring/` and are invoked by `orchestrator.py` / `invoke_agent.py` regardless of which harness rendered the config.

---

## Gap Analysis

### Gap 1: ANSI Color Output — Claude Code and π.dev renderers (LOW priority)

**Affected**: `render-claude.sh`, `render-pi-dev.py`  
**Issue**: Neither renderer checks `NO_COLOR` or uses ANSI colors for progress output.  
**Impact**: Minor UX inconsistency. Does not affect orchestration-layer monitoring.  
**Recommendation**: Add TTY detection + `NO_COLOR` check to `render-claude.sh` (bash). Add `NO_COLOR` check to `render-pi-dev.py` (Python).

### Gap 2: Per-Item Timing — Claude Code and π.dev renderers (LOW priority)

**Affected**: `render-claude.sh`, `render-pi-dev.py`  
**Issue**: No per-skill/per-agent timing reported during install.  
**Impact**: Users cannot identify slow skills on NFS-mounted home directories.  
**Recommendation**: Add `date +%s` timing around each rsync in `render-claude.sh`. Add `time.time()` timing in `render-pi-dev.py`.

### Gap 3: Streaming JSON Output — Claude Code and π.dev renderers (VERY LOW priority)

**Affected**: `render-claude.sh`, `render-pi-dev.py`  
**Issue**: No `--stream=json` mode for CI/CD pipelines.  
**Impact**: Copilot CLI has this via `src/harnesses/copilot_cli/streaming.py`. Other renderers lack it.  
**Recommendation**: Defer. The streaming Python helper could be generalized, but the use case is narrow.

### Gap 4: Documentation — All harnesses (MEDIUM priority)

**Affected**: All harnesses  
**Issue**: No integration guide explaining how to use Phase 3 monitoring features within each harness context.  
**Recommendation**: Create per-harness integration guides (done in this Phase D).

### Gap 5: Feature Parity Tests — All harnesses (HIGH priority)

**Affected**: All harnesses  
**Issue**: No automated tests verify consistent behavior across harnesses.  
**Recommendation**: Create `tests/test_phase3_feature_parity.py` (done in this Phase D).

---

## Priority Ranking

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| P1 | Feature parity tests | 2h | High — catches regressions |
| P2 | Documentation (integration guides) | 3h | Medium — developer clarity |
| P3 | ANSI/NO_COLOR in Claude Code renderer | 1h | Low — UX polish |
| P4 | ANSI/NO_COLOR in π.dev renderer | 1h | Low — UX polish |
| P5 | Per-item timing in Claude Code | 1h | Low — UX polish |
| P6 | Per-item timing in π.dev | 1h | Low — UX polish |
| P7 | Streaming JSON for Claude Code/π.dev | 4h | Very low — narrow use case |

---

## Implemented in Phase D

- ✅ `docs/PHASE-3-FEATURE-COVERAGE-AUDIT.md` — this document
- ✅ `docs/PHASE-3-INTEGRATION-PI-DEV.md` — π.dev integration guide
- ✅ `docs/PHASE-3-INTEGRATION-CLAUDE-CODE.md` — Claude Code integration guide
- ✅ `docs/PHASE-3-INTEGRATION-COPILOT-CLI.md` — Copilot CLI integration guide
- ✅ `tests/test_phase3_feature_parity.py` — feature parity test suite (10+ tests)
- ✅ ANSI/NO_COLOR support added to `render-claude.sh`
- ✅ ANSI/NO_COLOR support added to `render-pi-dev.py`
- ✅ Per-item timing added to `render-claude.sh`
- ✅ Per-item timing added to `render-pi-dev.py`
