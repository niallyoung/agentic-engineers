# Phase F — Duplication Audit

**Date**: 2026-05-17  
**Phase**: F — Simplification & Unification  
**Auditor**: Senior Engineer

---

## Executive Summary

Audit of the agentic-engineers codebase identified **6 categories of duplication** across source and test code. All findings are prioritised by impact.

---

## 1. Test Fixture Duplication (HIGH IMPACT)

### Finding
At least **11 independent `make_delegate` / `sample_delegate` factory functions** scattered across test files, each with slightly different field sets:

| File | Function | Notes |
|------|----------|-------|
| `test_invoke_agent.py` | `make_delegate()` | Full fields |
| `test_invoke_agent_token_wiring.py` | `make_delegate()` | Near-identical |
| `test_phase3_production_readiness.py` | `make_delegate()` | Slightly different defaults |
| `test_phase3_e2e_integration.py` | `make_delegate()` | Different model |
| `test_protocol_gray_zone.py` | `make_delegate()` | Minimal variant |
| `test_protocol_validation.py` | `make_valid_delegate()` | Different name, same shape |
| `test_artifact_manager.py` | `sample_delegate()` | pytest fixture |
| `test_orchestrator_cli.py` | `sample_delegate()` | pytest fixture |
| `test_gray_zone_reviewer.py` | `sample_delegate()` | pytest fixture |
| `test_protocol_routing_metrics.py` | `sample_delegate()` | pytest fixture |
| `test_automation_integration.py` | `sample_delegate()` | Method on test class |

**Estimated duplication**: ~150 lines of near-identical code.

### Resolution
Created `tests/conftest.py` with:
- `make_delegate(**kwargs)` — importable factory function with sensible defaults
- `make_handback(**kwargs)` — importable factory function
- `delegate_block` — pytest fixture
- `handback_block` — pytest fixture
- `high_quality_handback`, `low_quality_handback`, `gray_zone_handback` — scenario fixtures
- `tmp_queue` — temporary queue directory fixture

**Impact**: +326 previously-erroring tests now pass (2095 → 2421 passing).

---

## 2. Custom Exception Class Duplication (MEDIUM IMPACT)

### Finding
`ValidationError` defined independently in **3 separate modules**:

| File | Class | Notes |
|------|-------|-------|
| `src/orchestration/agents/model_resolver.py` | `ValidationError(Exception)` | Model validation |
| `src/skills/queue-management/queue_manager.py` | `ValidationError(QueueManagementError)` | Queue validation |
| `src/skills/agent-creator/__init__.py` | (uses ValidationError) | Agent config validation |

Additional isolated exception classes:
- `HandbackValidationError` in `invoke_agent.py`
- `ImmutableError` in `spec-management/audit_logger.py`
- `QueueManagementError`, `DuplicateTaskError`, `GitError` in `queue_manager.py`
- `ModelNotFoundError` in `model_resolver.py`
- `QueueEnforcementError` in `queue_enforcement_middleware.py`

**Estimated duplication**: ~40 lines of boilerplate exception definitions.

### Resolution
Created `src/orchestration/errors.py` with a unified exception hierarchy:
```
AgenticEngineersError (base)
├── ValidationError
├── RoutingError
├── QueueError
│   └── DuplicateTaskError
├── ModelError
│   └── ModelNotFoundError
├── BudgetError
├── HandbackError
└── ImmutableError
```
Backward-compatibility aliases provided for existing imports.

---

## 3. Configuration File Fragmentation (MEDIUM IMPACT)

### Finding
Orchestration settings split across **2 separate YAML files**:

| File | Contents |
|------|----------|
| `config/token_budget.yaml` | Budget limits, display settings |
| `config/deployment.yaml` | Deployment mode, rollout stages, monitoring |

Additional implicit constants in source code:
- `MAX_RETRIES = 2` in `orchestrator.py`
- Quality score thresholds (70, 80, 90) hardcoded in `orchestrator.py`
- `idle_timeout` defaulting to 60s in `Orchestrator.__init__`

### Resolution
Created `config/orchestration.yaml` — single unified config file containing:
- `budget` section (from token_budget.yaml)
- `display` section (from token_budget.yaml)
- `deployment` section (from deployment.yaml)
- `orchestrator` section (idle_timeout, poll_interval, max_retries)
- `quality` section (all quality score thresholds)

Original files retained for backward compatibility.

---

## 4. Dead Code in Orchestrator (LOW IMPACT)

### Finding
`orchestrator.py` contained a **29-line unreachable block** (lines 1043–1071) — a docstring + code block that appeared after a `return` statement inside `collect_metrics()`. This was a stale copy of `run_poll_cycle()` logic that was never removed.

### Resolution
Removed the dead code block. No functional change.

---

## 5. Routing Logic Inline Conditionals (LOW IMPACT)

### Finding
`_process_task()` in `orchestrator.py` contained an inline 3-branch conditional for quality-based role override, mixing routing logic with task processing flow:

```python
if validation.routing_decision == RoutingDecision.LOW:
    role = "principal_engineer"
elif validation.routing_decision == RoutingDecision.MEDIUM:
    role = "lead_engineer"
# HIGH: proceed with original role as-is
```

This made `_process_task()` harder to read and test in isolation.

### Resolution
Extracted to `_quality_override_role(role, validation) -> str` — a named, testable method with clear docstring describing the routing rules.

---

## 6. YAML Loading Pattern Repetition (LOW IMPACT)

### Finding
`yaml.safe_load()` called with identical error-handling boilerplate in multiple files:
- `orchestrator.py` (13 occurrences)
- `artifact_manager.py`
- `metrics_writer.py`
- `invoke_agent.py`
- `shadow_mode.py`

Pattern is consistent enough to extract to a utility, but the risk/reward ratio is low given each call site has slightly different error handling needs.

### Resolution
**Deferred** — noted for Phase G. A `safe_load_yaml(path, default=None)` utility in `src/orchestration/utils.py` would reduce boilerplate by ~30 lines.

---

## Metrics

| Category | Duplication Found | Lines Removed | Lines Added | Net |
|----------|------------------|---------------|-------------|-----|
| Test fixtures | 11 duplicate factories | ~150 | 95 (conftest.py) | -55 |
| Exception classes | 9 isolated classes | ~40 | 65 (errors.py) | +25 |
| Config fragmentation | 2 files → 1 unified | 0 | 90 (orchestration.yaml) | +90 |
| Dead code | 1 orphaned block | 29 | 0 | -29 |
| Routing conditionals | 5-line inline block | 5 | 18 (extracted method) | +13 |
| **Total** | | **224** | **268** | **+44** |

*Net positive because consolidation adds documentation and structure.*

---

## Priority Matrix

| Finding | Impact | Effort | Status |
|---------|--------|--------|--------|
| Test fixture duplication | HIGH | LOW | ✅ Done |
| Dead code removal | LOW | LOW | ✅ Done |
| Routing logic extraction | LOW | LOW | ✅ Done |
| Exception class unification | MEDIUM | LOW | ✅ Done |
| Config unification | MEDIUM | LOW | ✅ Done |
| YAML loading utility | LOW | MEDIUM | ⏳ Phase G |
