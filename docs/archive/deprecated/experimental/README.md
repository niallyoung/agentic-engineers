# Archived Experimental Code

This directory contains experimental implementations and reference code that was removed during the Phase 6 consolidation (May 17, 2026).

## Files

### Routing & Decision Engines (Superseded by AGENTS.md)
- **routing_agent.py** - Early routing implementation, superseded by TaskRouter in orchestrator.py
- **smart_router.py** - Advanced routing logic, superseded by AGENTS.md decision tree
- **decision_engine.py** - Experimental decision logic, superseded by TaskRouter
- **gray_zone_reviewer.py** - Edge case handling, superseded by quality gates

### Gradual Rollout & Shadow Mode (Experimental Features)
- **gradual_rollout.py** - Gradual deployment feature (not used)
- **shadow_mode.py** - Shadow mode testing feature (not used)

### Reference Implementations (Documentation)
- **ENGINEER-IMPLEMENTATION-REFERENCE.py** - Example engineer agent implementation
- **ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py** - Example orchestrator implementation
- **example_end_to_end.py** - End-to-end workflow example

## Why Archived?

1. **Duplication**: Multiple implementations of the same responsibility (routing, quality evaluation, etc.)
2. **Spec Compliance**: These files violated the SPEC by implementing work outside the agent/skill model
3. **Clarity**: Framework is clearer with single source of truth per responsibility
4. **Maintenance**: Reduced codebase complexity and maintenance burden

## Canonical Implementations

The canonical implementations are now:

- **Routing**: `src/orchestration/agents/orchestrator.py` (TaskRouter class)
- **Quality Evaluation**: `src/orchestration/agents/quality_validator.py` + `src/skills/quality-evaluation/`
- **Protocol Validation**: `src/skills/protocol-validator/`
- **Queue Management**: `src/skills/queue-management/`
- **Agent Definitions**: `~/.config/opencode/agents/`

## If You Need This Code

If you need to reference or restore any of these files:

1. Check git history: `git log --all -- src/orchestration/agents/routing_agent.py`
2. Restore from git: `git checkout <commit> -- src/orchestration/agents/routing_agent.py`
3. Review the architecture audit: `docs/ARCHITECTURE-AUDIT-2026-05-17.md`

## Consolidation Date

Archived: May 17, 2026 (Phase 6 Consolidation)
