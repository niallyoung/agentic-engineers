# Archive Manifest

This directory contains code and documentation archived during the Phase 6 Consolidation Sprint (2026-05-17).

## experimental/

Experimental code modules removed from active codebase. These were research/prototype implementations
that have been superseded by the canonical agents+skills model.

| File | Description | Archived |
|------|-------------|---------|
| gray_zone_reviewer.py | Lead Engineer quality gate for 70–79 score HANDBACKs | 2026-05-17 |
| routing_agent.py | Early routing agent prototype | 2026-05-17 |
| smart_router.py | Intelligent task routing with skill integration | 2026-05-17 |
| decision_engine.py | Decision engine for task routing | 2026-05-17 |
| shadow_mode.py | Shadow mode execution framework | 2026-05-17 |
| gradual_rollout.py | Gradual rollout traffic management | 2026-05-17 |
| ENGINEER-IMPLEMENTATION-REFERENCE.py | Engineer agent implementation reference | 2026-05-17 |
| ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py | Orchestrator implementation reference | 2026-05-17 |
| example_end_to_end.py | End-to-end example script | 2026-05-17 |

Note: `gray_zone_reviewer.py` logic was inlined into `orchestrator.py` as `analyze_handback_for_gray_zone()`.

## experimental-tests/

Test files for archived experimental modules.

| File | Tests For |
|------|-----------|
| test_decision_engine.py | decision_engine.py |
| test_gradual_rollout.py | gradual_rollout.py |
| test_gray_zone_reviewer.py | gray_zone_reviewer.py |
| test_routing_agent.py | routing_agent.py |
| test_shadow_mode.py | shadow_mode.py |
| test_smart_router.py | smart_router.py |
| test_skill_integration.py | smart_router.py skill integration |
| test_phase3_e2e_integration.py | Phase 3 E2E integration |
| test_phase3_gradual_rollout_e2e.py | Gradual rollout E2E |
| test_phase3_shadow_mode_e2e.py | Shadow mode E2E |
| test_protocol_gray_zone.py | Gray zone protocol |

## documentation/

Old phase documentation and experimental feature guides superseded by current docs.

| File | Description |
|------|-------------|
| PHASE-1-EXECUTION-LOG.md | Phase 1 execution log |
| PHASE-3-*.md | Phase 3 implementation specs and reports |
| PHASE-4-*.md | Phase 4 design documents |
| PHASE-5-COMPLETE.md | Phase 5 completion report |
| SHADOW_MODE.md | Shadow mode documentation |
| SHADOW_MODE_RUNBOOK.md | Shadow mode runbook |
| DRY_RUN_MODE.md | Dry run mode documentation |

## bin/

Redundant entry point scripts replaced by `bin/orchestrator_daemon.py`.

| File | Description |
|------|-------------|
| run-automation-controller.sh | Shell wrapper for automation controller |
| orchestrator-autopilot.sh | Legacy bash autopilot loop |

## scripts/

Utility scripts archived (not converted to skills per consolidation plan).

| File | Description |
|------|-------------|
| dry_run_examples.py | Dry-run mode demonstration script |
| validate-opencode-config.sh | OpenCode config validation script |
| check-framework-approval.sh | Framework approval check script |
