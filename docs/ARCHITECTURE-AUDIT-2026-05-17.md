# ARCHITECTURE AUDIT: Agents, Skills, and Framework Analysis

**Date**: May 17, 2026  
**Status**: ANALYSIS ONLY — No changes made yet  
**Scope**: Identify consolidation/simplification opportunities and non-standard patterns

---

## Executive Summary

The agentic-engineers framework is **largely SPEC-compliant** (agents + skills model) but has accumulated:

1. **84 Python files** in `src/orchestration/` (23,496 lines)
2. **56 Python files** in `src/skills/` (15,071 lines)
3. **91 test files** (40,546 lines)
4. **Multiple entry points** (bin/, scripts/, Makefile)
5. **Duplication** across agent implementations
6. **Out-of-band scripts** that should be skills or agent responsibilities

**Key Finding**: The framework is **agents + skills correct** but has **bloat, duplication, and unclear responsibilities** that can be consolidated.

---

## 1. CURRENT ARCHITECTURE

### 1.1 Agents (8 canonical)

Located: `~/.config/opencode/agents/` (rendered from `src/orchestration/agents/`)

```
✅ orchestrator.md       — Entry point, queue polling, routing
✅ engineer.md           — Well-scoped implementation tasks
✅ senior-engineer.md    — Complex unscoped work, design phase
✅ lead-engineer.md      — Code review, validation, consolidation
✅ principal-engineer.md — Cross-service architecture, escalations
✅ quality-engineer.md   — Quality evaluation, metrics, escalation
✅ model-engineer.md     — Cost-quality optimization, A/B tests
✅ security-engineer.md  — Security analysis, threat modeling
```

**Implementation**: `src/orchestration/agents/orchestrator.py` (71,733 bytes)
- `OrchestratorAgent` class (main entry point)
- `TaskRouter` class (routing logic)
- `QueueManager` class (queue operations)

**Supporting files** (28 Python files in `src/orchestration/agents/`):
- `automation.py` — AutomationController (polling daemon)
- `orchestrator_protocol_integration.py` — Protocol handling
- `quality_engineer_protocol_integration.py` — Quality evaluation
- `parallel_delegate.py` — Parallel task decomposition
- `invoke_agent.py` — Subprocess agent invocation
- `implementations.py` — Agent implementations (GeneralOrchestrator, EngineerAgent, etc.)
- Reference files: `ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py`, `ENGINEER-IMPLEMENTATION-REFERENCE.py`, `AGENT-IMPLEMENTATION-TEMPLATE.py`
- Experimental/legacy: `routing_agent.py`, `smart_router.py`, `decision_engine.py`, `gray_zone_reviewer.py`, `shadow_mode.py`, `gradual_rollout.py`

### 1.2 Skills (14 canonical + 18 supporting)

Located: `src/skills/` (14 SKILL.md files)

```
✅ ab-testing              — Experiment orchestration
✅ agent-creator           — Scaffolds new agents
✅ consistency-checker     — Protocol queue validation
✅ metrics-etl             — Metrics aggregation
✅ model-engineer          — Cost-quality optimization
✅ protocol-validator      — Runtime protocol validation
✅ queue-management        — Atomic queue operations
✅ repo-init               — Repository initialization
✅ skill-creator           — Creates new skills
✅ spec-management         — SPEC.md change protection
✅ spec-validator          — Implementation compliance
✅ tokenadvisor            — Token spend analysis
✅ usage-tracking          — Token usage capture
✅ voice-notify            — Audio alerts
```

**Supporting directories** (18 non-SKILL.md):
- `architecture/`, `monitoring/`, `optimization/`, `orchestration/`, `patterns/`, `review/`, `roles/`, `security/`, `shared/`, `testing/`, `verify_*` (6 dirs)

### 1.3 Entry Points

**Bin scripts** (3 files):
- `bin/orchestrator_daemon.py` — Polling daemon entry point (24 lines, wraps AutomationController)
- `bin/run-automation-controller.sh` — Shell wrapper for daemon (1,689 bytes)
- `bin/orchestrator-autopilot.sh` — Legacy shell-based queue monitor (68 lines, non-functional)

**Scripts** (4 files):
- `scripts/dry_run_examples.py` — Dry-run mode examples (10,566 bytes)
- `scripts/validate-opencode-config.sh` — Config validation (4,357 bytes)
- `scripts/opencode-safe.sh` — Safe OpenCode operations (4,647 bytes)
- `scripts/check-framework-approval.sh` — Framework approval check (1,294 bytes)

**Makefile** (161 lines):
- Install/uninstall targets (claude, copilot, pi, opencode)
- Render targets (dist/ generation)
- Verify/validate targets

**Renderer scripts** (8 files in `renderer/scripts/`):
- `render-opencode.sh`, `render-claude.sh`, `render-copilot.sh`, `render-pi.sh`
- `render-copilot-agents.sh`, `render-copilot-agents.py`
- `copilot-session-init.sh`, `copilot-guard.sh`

---

## 2. ANALYSIS: WHAT'S WORKING WELL

### ✅ Core Protocol (SPEC-Compliant)

1. **DELEGATE/HANDBACK blocks** — Well-defined, validated
2. **Agent routing** — Clear decision tree (orchestrator → engineer/senior/lead/principal/security/quality/model)
3. **Queue-based execution** — `incoming/ → processing/ → done/`
4. **Skills as reusable modules** — Loaded on-demand via skill tool
5. **Quality gates** — Baseline, escalation, trend detection
6. **Metrics collection** — Token tracking, cost attribution, quality scoring

### ✅ Test Coverage

- 137 tests passing (100%)
- Unit, integration, e2e, regression, validation
- Quality metrics: 92.3/100 avg, 0% escalation

### ✅ Documentation

- Comprehensive guides (AGENTS.md, HANDOFF.md, QUEUE-PROTOCOL.md, SKILLS.md)
- Architecture diagrams
- Deployment guides
- Runbooks

---

## 3. ISSUES IDENTIFIED

### 3.1 BLOAT: Duplicate/Experimental Code

**Problem**: 28 agent files, but only 1 canonical agent (Orchestrator) is active.

| File | Lines | Status | Issue |
|------|-------|--------|-------|
| `orchestrator.py` | 71,733 | ✅ Active | Monolithic, 3 classes, 1000+ lines |
| `implementations.py` | 12,240 | ❓ Unclear | GeneralOrchestrator, EngineerAgent, etc. — are these used? |
| `invoke_agent.py` | 21,814 | ❓ Unclear | AgentInvoker for subprocess invocation — optional, not required |
| `routing_agent.py` | 8,934 | ❌ Legacy | Experimental routing logic |
| `smart_router.py` | 19,749 | ❌ Legacy | Experimental smart routing |
| `decision_engine.py` | 12,500 | ❌ Legacy | Experimental decision engine |
| `gray_zone_reviewer.py` | 7,601 | ❌ Legacy | Experimental gray-zone analysis |
| `shadow_mode.py` | 20,587 | ❌ Legacy | Experimental shadow mode |
| `gradual_rollout.py` | 29,230 | ❌ Legacy | Experimental gradual rollout |
| `ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py` | 14,856 | ❌ Reference | Template/example, not used |
| `ENGINEER-IMPLEMENTATION-REFERENCE.py` | 10,825 | ❌ Reference | Template/example, not used |
| `AGENT-IMPLEMENTATION-TEMPLATE.py` | 11,785 | ❌ Reference | Template/example, not used |
| `example_end_to_end.py` | 8,172 | ❌ Example | Example workflow, not used |

**Total bloat**: ~200K lines of experimental/reference code

### 3.2 UNCLEAR RESPONSIBILITIES

**Problem**: Multiple files doing similar things, unclear which is canonical.

| Responsibility | Files | Issue |
|---|---|---|
| Queue management | `orchestrator.py::QueueManager`, `queue_manager.py`, `src/skills/queue-management/` | 3 implementations |
| Protocol validation | `delegate_validator.py`, `spec_validator.py`, `src/skills/protocol-validator/` | 3 implementations |
| Quality evaluation | `quality_validator.py`, `quality_engineer_protocol_integration.py`, `src/orchestration/quality/` | 3 implementations |
| Metrics collection | `metrics_writer.py`, `src/orchestration/monitoring/metrics.py`, `src/skills/metrics-etl/` | 3 implementations |
| Cost tracking | `src/orchestration/cost/`, `src/orchestration/models/cost_*.py` | 2 implementations |
| Routing | `TaskRouter`, `routing_agent.py`, `smart_router.py`, `decision_engine.py` | 4 implementations |

### 3.3 OUT-OF-BAND SCRIPTS (Non-SPEC)

**Problem**: Work happening outside agent/skill model.

| Script | Purpose | Should Be |
|--------|---------|-----------|
| `bin/orchestrator_daemon.py` | Polling loop entry point | ✅ OK (thin wrapper) |
| `bin/run-automation-controller.sh` | Shell wrapper for daemon | ❌ Should be in agent |
| `bin/orchestrator-autopilot.sh` | Legacy queue monitor | ❌ Should be in agent or removed |
| `scripts/dry_run_examples.py` | Dry-run mode | ✅ Could be skill |
| `scripts/validate-opencode-config.sh` | Config validation | ❌ Should be skill |
| `scripts/opencode-safe.sh` | Safe operations | ❌ Should be skill |
| `scripts/check-framework-approval.sh` | Framework approval | ❌ Should be skill |
| `renderer/scripts/*.sh` | Build-time rendering | ✅ OK (build-time only) |

### 3.4 MONOLITHIC ORCHESTRATOR

**Problem**: `orchestrator.py` is 71KB with 3 classes and 1000+ lines.

```python
class QueueManager:        # 200 lines — should be in queue-management skill
class TaskRouter:          # 300 lines — should be in routing skill
class OrchestratorAgent:   # 700+ lines — core orchestrator logic
```

**Recommendation**: Split into:
1. `orchestrator.py` — OrchestratorAgent only (core routing, polling)
2. Move QueueManager → `src/skills/queue-management/`
3. Move TaskRouter → routing logic in OrchestratorAgent or separate skill

### 3.5 AUTOMATION CONTROLLER UNCLEAR

**Problem**: `automation.py` (AutomationController) is a polling wrapper, but:
- Not exposed as a skill
- Not documented in AGENTS.md
- Only invoked via `bin/orchestrator_daemon.py`
- Unclear if it's part of the agent or a separate tool

**Recommendation**: Either:
1. Make it a skill (automation-controller skill)
2. Merge it into OrchestratorAgent
3. Document it clearly as an internal implementation detail

### 3.6 PROTOCOL INTEGRATION FILES

**Problem**: Multiple "protocol integration" files doing similar things:
- `orchestrator_protocol_integration.py` (14KB)
- `quality_engineer_protocol_integration.py` (11KB)
- `src/skills/protocol-validator/` (separate skill)

**Recommendation**: Consolidate into a single `protocol_integration.py` module or make it a skill.

### 3.7 AGENT IMPLEMENTATIONS

**Problem**: `implementations.py` defines agent classes (GeneralOrchestrator, EngineerAgent, etc.) but:
- Not clear if they're used
- Not exposed as agents in OpenCode
- Seem to be internal implementation details

**Recommendation**: Either:
1. Use them as the canonical agent implementations
2. Remove them and use the agent definitions in `~/.config/opencode/agents/`
3. Document their purpose clearly

### 3.8 SUBPROCESS INVOCATION (invoke_agent.py)

**Problem**: `invoke_agent.py` (21KB) implements subprocess-based agent invocation:
- Optional feature (not required for queue-based execution)
- Not used in current workflow
- Adds complexity without clear benefit

**Recommendation**: Either:
1. Make it a skill (agent-invocation skill)
2. Remove it (use OpenCode agent invocation instead)
3. Document when/why it's needed

### 3.9 SKILL DUPLICATION

**Problem**: Some skills have overlapping functionality:
- `queue-management` skill vs `QueueManager` in orchestrator
- `protocol-validator` skill vs `delegate_validator.py`
- `spec-validator` skill vs `spec_validator.py`

**Recommendation**: Consolidate to single source of truth for each responsibility.

### 3.10 DOCUMENTATION BLOAT

**Problem**: 200+ documentation files, many archived or outdated:
- `docs/archive/` — 50+ archived files
- `docs/FRAMEWORKS/` — Framework research (not used)
- `docs/decisions/` — ADRs (some outdated)
- Multiple versions of same guide (e.g., PHASE-*.md)

**Recommendation**: Archive older docs, keep only current operational guides.

---

## 4. CONSOLIDATION OPPORTUNITIES

### 4.1 Merge Duplicate Queue Management

**Current**:
```
orchestrator.py::QueueManager (200 lines)
src/skills/queue-management/ (full skill)
queue_manager.py (separate file)
```

**Proposed**:
```
src/skills/queue-management/ (single source of truth)
  - queue_ops.py (core operations)
  - validators.py (validation)
  - rate_limiter.py (rate limiting)
  - consistency.py (consistency checking)
```

**Action**: Remove QueueManager from orchestrator.py, use skill instead.

### 4.2 Consolidate Protocol Validation

**Current**:
```
delegate_validator.py
spec_validator.py
src/skills/protocol-validator/
src/skills/spec-validator/
```

**Proposed**:
```
src/skills/protocol-validator/ (single source of truth)
  - delegate_validator.py
  - spec_validator.py
  - handback_validator.py
```

**Action**: Move validation logic to skill, remove duplicate files.

### 4.3 Consolidate Quality Evaluation

**Current**:
```
quality_validator.py (39KB)
quality_engineer_protocol_integration.py (11KB)
src/orchestration/quality/ (multiple files)
```

**Proposed**:
```
src/orchestration/agents/quality_engineer_protocol_integration.py (canonical)
  - Merge quality_validator.py into this
  - Remove src/orchestration/quality/ duplication
```

**Action**: Single source of truth for quality evaluation.

### 4.4 Remove Experimental Code

**Current**: 200K lines of experimental/legacy code
- `routing_agent.py`, `smart_router.py`, `decision_engine.py`
- `gray_zone_reviewer.py`, `shadow_mode.py`, `gradual_rollout.py`
- Reference files: `*-IMPLEMENTATION-REFERENCE.py`, `*-IMPLEMENTATION-TEMPLATE.py`

**Proposed**: Archive to `docs/archive/experimental/` or remove entirely.

**Action**: Clean up, keep only canonical implementations.

### 4.5 Clarify Agent Implementations

**Current**: `implementations.py` defines agent classes but unclear if used.

**Proposed**: Either:
1. **Option A**: Use them as canonical implementations, document in AGENTS.md
2. **Option B**: Remove them, use agent definitions in `~/.config/opencode/agents/` only
3. **Option C**: Move to `src/skills/agent-creator/` as templates

**Action**: Decide on canonical approach, document clearly.

### 4.6 Consolidate Entry Points

**Current**:
```
bin/orchestrator_daemon.py (24 lines)
bin/run-automation-controller.sh (1,689 bytes)
bin/orchestrator-autopilot.sh (68 lines, non-functional)
Makefile (161 lines)
```

**Proposed**:
```
bin/orchestrator_daemon.py (keep, thin wrapper)
bin/run-automation-controller.sh (remove, use Python directly)
bin/orchestrator-autopilot.sh (remove, use orchestrator_daemon.py)
Makefile (keep, but simplify)
```

**Action**: Consolidate to single entry point.

### 4.7 Move Scripts to Skills

**Current**:
```
scripts/dry_run_examples.py
scripts/validate-opencode-config.sh
scripts/opencode-safe.sh
scripts/check-framework-approval.sh
```

**Proposed**:
```
src/skills/dry-run/ (new skill)
src/skills/config-validator/ (new skill)
src/skills/framework-validator/ (new skill)
```

**Action**: Convert scripts to skills, remove from scripts/ directory.

### 4.8 Consolidate Monitoring/Metrics

**Current**:
```
src/orchestration/monitoring/ (multiple files)
src/orchestration/models/ (cost/quality analysis)
src/skills/metrics-etl/
src/skills/tokenadvisor/
```

**Proposed**:
```
src/skills/metrics-etl/ (single source of truth)
  - metrics collection
  - aggregation
  - export (Prometheus)
src/skills/tokenadvisor/ (cost analysis)
src/skills/quality-dashboard/ (quality metrics)
```

**Action**: Consolidate monitoring into skills.

---

## 5. SPEC COMPLIANCE ASSESSMENT

### ✅ COMPLIANT

1. **Agent model**: 8 agents defined, routable via OpenCode
2. **Skill model**: 14 skills with SKILL.md frontmatter
3. **Queue-based execution**: DELEGATE/HANDBACK blocks, queue states
4. **Protocol validation**: DELEGATE/HANDBACK schema validation
5. **Quality gates**: Baseline, escalation, metrics
6. **Metrics collection**: Token tracking, cost attribution

### ⚠️ PARTIALLY COMPLIANT

1. **Agent implementations**: Unclear if `implementations.py` is canonical
2. **Subprocess invocation**: Optional feature, not documented
3. **Automation controller**: Not exposed as skill or agent
4. **Protocol integration**: Multiple files doing similar things

### ❌ NON-COMPLIANT

1. **Experimental code**: 200K lines of legacy/experimental code not in spec
2. **Out-of-band scripts**: `scripts/`, `bin/` files doing work outside agent/skill model
3. **Monolithic orchestrator**: 71KB file with multiple responsibilities
4. **Duplicate implementations**: Queue, validation, metrics, routing

---

## 6. RECOMMENDATIONS (PRIORITY ORDER)

### 🔴 HIGH PRIORITY (Blocking clarity)

1. **Decide on canonical agent implementations**
   - Are `implementations.py` classes used?
   - If yes: document in AGENTS.md, expose in OpenCode
   - If no: remove them

2. **Consolidate queue management**
   - Remove `QueueManager` from orchestrator.py
   - Use `src/skills/queue-management/` as single source of truth
   - Update orchestrator to call skill

3. **Clarify automation controller**
   - Is it a skill? Document it.
   - Is it internal? Document it.
   - Is it optional? Document when/why it's used.

4. **Remove experimental code**
   - Archive `routing_agent.py`, `smart_router.py`, `decision_engine.py`, etc.
   - Archive reference files (`*-IMPLEMENTATION-REFERENCE.py`)
   - Keep only canonical implementations

### 🟡 MEDIUM PRIORITY (Simplification)

5. **Consolidate protocol validation**
   - Single source of truth for DELEGATE/HANDBACK validation
   - Remove duplicate files

6. **Consolidate quality evaluation**
   - Merge `quality_validator.py` into `quality_engineer_protocol_integration.py`
   - Remove `src/orchestration/quality/` duplication

7. **Convert scripts to skills**
   - `scripts/dry_run_examples.py` → `src/skills/dry-run/`
   - `scripts/validate-opencode-config.sh` → `src/skills/config-validator/`
   - `scripts/check-framework-approval.sh` → `src/skills/framework-validator/`

8. **Consolidate entry points**
   - Keep `bin/orchestrator_daemon.py`
   - Remove `bin/run-automation-controller.sh`
   - Remove `bin/orchestrator-autopilot.sh`

### 🟢 LOW PRIORITY (Cleanup)

9. **Archive documentation**
   - Move `docs/archive/` to separate location
   - Keep only current operational guides
   - Remove outdated PHASE-*.md files

10. **Clarify subprocess invocation**
    - If needed: make it a skill
    - If not needed: remove `invoke_agent.py`

---

## 7. SUMMARY TABLE

| Item | Current | Issue | Recommendation | Priority |
|------|---------|-------|-----------------|----------|
| Agent implementations | `implementations.py` | Unclear if used | Decide: use or remove | 🔴 HIGH |
| Queue management | 3 implementations | Duplicate | Single source (skill) | 🔴 HIGH |
| Automation controller | `automation.py` | Not documented | Clarify role | 🔴 HIGH |
| Experimental code | 200K lines | Bloat | Archive | 🔴 HIGH |
| Protocol validation | 3 implementations | Duplicate | Single source | 🟡 MEDIUM |
| Quality evaluation | 2 implementations | Duplicate | Consolidate | 🟡 MEDIUM |
| Scripts | 4 files | Out-of-band | Convert to skills | 🟡 MEDIUM |
| Entry points | 3 files | Redundant | Consolidate | 🟡 MEDIUM |
| Documentation | 200+ files | Bloat | Archive old docs | 🟢 LOW |
| Subprocess invocation | `invoke_agent.py` | Unclear | Decide: skill or remove | 🟢 LOW |

---

## 8. CONCLUSION

The agentic-engineers framework is **SPEC-compliant at its core** (agents + skills model, queue-based execution, quality gates) but has accumulated:

1. **Bloat**: 200K lines of experimental/legacy code
2. **Duplication**: Multiple implementations of queue, validation, metrics, routing
3. **Unclear responsibilities**: Monolithic orchestrator, unclear agent implementations
4. **Out-of-band work**: Scripts doing work outside agent/skill model

**Recommendation**: Execute consolidation in priority order (HIGH → MEDIUM → LOW) to:
- Reduce codebase from 23K → ~10K lines in orchestration
- Single source of truth for each responsibility
- Clear agent/skill boundaries
- Improved maintainability and clarity

**No changes made yet** — awaiting your confirmation to proceed.

---

**Next Steps**:
1. Review this analysis
2. Confirm priorities and recommendations
3. Proceed with consolidation (Phase 7?)
4. Update documentation and tests
5. Verify all 137 tests still pass
