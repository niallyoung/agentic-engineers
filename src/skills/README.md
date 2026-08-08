# agentic-engineers Agent Framework

Self-contained, agent-driven SDLC orchestration system. **No external dependencies.** All work flows between agents via DELEGATE/HANDBACK/FEEDBACK protocol. Agents delegate to agents; recursively.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Orchestrator (High-level API)                     │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────────┐  ┌──────────────────────┐
│ Orchestrator │  │ Execute Selected     │
│ (Route task) │  │ Agent (plan/design)  │
└──────┬───────┘  └──────────┬───────────┘
       │                     │
       └─────────┬───────────┘
                 ▼
         ┌──────────────────┐
         │ Quality Engineer │
         │ (Post-impl QA)   │
         └────────┬─────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
    ┌─────────┐    ┌───────────────────┐
    │ Model   │    │ Quality Gate      │
    │Engineer │    │ (5 sub-agents)    │
    └─────────┘    └───────────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              ┌──────────────┐    ┌──────────────┐
              │PROCEED       │    │ESCALATE      │
              └──────────────┘    └──────────────┘
```

## Components

### 1. Base Framework (`__init__.py`)

- **Agent**: Abstract base class for all agents
  - `execute(delegate_block: Dict) -> Dict`: Main entry point
  - `_validate_input()`: Validates DELEGATE block
  - `do_work()`: Override in subclass
  
- **AgentConfig**: Configuration for each agent
  - `name`, `model`, `effort`, `role`, `description`
  
- **AGENTS Registry**: All 14 agent configurations

### 2. Implementations (`implementations.py`)

Complete implementations of all 13 agents + QG Orchestrator:

**SDLC Agents:**
- `GeneralOrchestrator` - Routes work to specialists
- `EngineerAgent` - Executes pre-planned tasks
- `SeniorEngineerAgent` - Analyzes & plans complex work
- `LeadEngineerAgent` - Code review & architectural guidance
- `PrincipalEngineerAgent` - Cross-service architecture
- `QualityEngineerAgent` - Post-implementation quality gate
- `ModelEngineerAgent` - Confidence scoring & recommendations
- `SecurityEngineerAgent` - Security analysis & threat modeling

**Quality Gate Sub-Agents:**
- `SecurityAgentQG` - Credential & vulnerability scanning
- `TestingAgent` - Test coverage & metrics
- `MetricsAgent` - System health scoring
- `HealingAgent` - Config validation & auto-fixes
- `SpecEngineerAgent` - Spec drift detection

**Gateway:**
- `QualityGateOrchestrator` - Runs 5 sub-agents in parallel

### 3. Artifact Management (`artifact_manager.py`)

Serialize/deserialize DELEGATE/HANDBACK/FEEDBACK blocks:

```python
artifacts = ArtifactManager()

# Write blocks
artifacts.write_delegate(task_id, delegate_dict)
artifacts.write_handback(task_id, handback_dict)
artifacts.write_feedback(task_id, feedback_dict)

# Read blocks
delegate = artifacts.read_delegate(task_id)
handback = artifacts.read_handback(task_id)

# List all artifacts for a date
artifacts_list = artifacts.list_artifacts("2026-04-29")

# Export as JSON
json_str = artifacts.export_json(task_id)
```

Artifacts are stored in `artifacts/YYYY-MM-DD/` directory for date-keyed archival.

### 4. Workflow Orchestrator (`workflow.py`)

High-level API for executing complete task pipelines:

```python
wf = WorkflowOrchestrator()

result = wf.execute_task(
    description="Fix token validation",
    scope="Add grace period to exp claim check",
    complexity="medium",
    has_plan=True,
    is_security=False
)

# Result includes:
# - orchestrator routing decision
# - executor output (quality score, deliverables)
# - quality engineer review
# - model engineer recommendations
# - quality gate decision (PROCEED/ESCALATE)

print(wf.summary())  # Execution statistics
```

### 5. Examples & Tests

**End-to-End Example** (`example_end_to_end.py`)
```bash
python orchestration/agents/example_end_to_end.py
```

Demonstrates a complete task execution:
1. Orchestrator routes
2. Engineer executes
3. Quality Engineer reviews
4. Model Engineer recommends
5. Quality Gate decides

**Testing Harness** (`testing_harness.py`)
```bash
python orchestration/agents/testing_harness.py
```

Runs 10 test scenarios covering:
- ✅ Clean commit (expect PROCEED)
- ❌ Security issue (expect ESCALATE)
- ❌ Test failure (expect ESCALATE)
- ❌ Metrics degradation (expect ESCALATE)
- ❌ Config drift (expect ESCALATE)
- ❌ Spec Drift TYPE_A (expect ESCALATE)
- ❌ Spec Drift TYPE_B (expect ESCALATE)
- ❌ Spec Drift TYPE_C (expect ESCALATE)
- ❌ Spec Drift TYPE_D (expect ESCALATE)
- ❌ Mixed issues (expect ESCALATE)

## DELEGATE/HANDBACK Protocol

### DELEGATE Block (Input)

```yaml
handoff_type: DELEGATE
task_id: 2026-04-29-fix-auth-abc123
role: engineer
model: claude-haiku-4.5
effort: high  # low, medium, high, max
scope: "Add timeout grace period to authentication service validation"
complexity: medium  # low, medium, high
has_plan: true
is_security_scoped: false
context:
  file: lambda/api/main.go:92
  error: Token rejected after 1hr
  root_cause: clock skew
plan:
  - Add grace period to exp check
  - Write test TestTokenExpiryGracePeriod
  - Run 'make verify'
success_criteria:
  - make verify passes
  - Mobile e2e auth passes
```

### HANDBACK Block (Output)

```yaml
handoff_type: HANDBACK
task_id: 2026-04-29-fix-auth-abc123
timestamp: 2026-04-29T14:32:00
status: PASS  # PASS or ESCALATE
severity: PASS  # PASS, LOW, MEDIUM, HIGH
confidence: 0.92  # 0.0-1.0
deliverables:
  - Task completed per plan
execution_results:
  - step: 1
    description: Add grace period
    status: SUCCESS
success_criteria_results:
  - criterion: make verify passes
    passed: true
quality_score: 95  # 0-100
token_metrics:
  input_tokens: 340
  output_tokens: 580
  total_tokens: 920
```

## Agent Models & Costs

| Agent | Model | Effort | Est. Cost |
|-------|-------|--------|-----------|
| Orchestrator | Haiku 4.5 | low | $0.003 |
| Engineer | Haiku 4.5 | high | $0.015 |
| Senior Engineer | Sonnet 4.6 | high | $0.075 |
| Lead Engineer | Sonnet 4.6 | high | $0.075 |
 | Principal Engineer | Opus 4.6 | high | $0.375 |
| Quality Engineer | Sonnet 4.6 | medium | $0.045 |
| Model Engineer | Haiku 4.5 | medium | $0.009 |
| Security Engineer | Fable 5 | max | $0.36 |
| Security Agent (QG) | Fable 5 | high | $0.36 |
| Testing Agent | Haiku 4.5 | medium | $0.009 |
| Metrics Agent | Haiku 4.5 | medium | $0.009 |
| Healing Agent | Sonnet 4.6 | medium | $0.045 |
| Spec Engineer | Sonnet 4.6 | medium | $0.045 |
| QG Orchestrator | Sonnet 4.6 | medium | $0.045 |

**Quality Gate baseline cost: $0.31/commit** (all 5 sub-agents in parallel)

## Routing Decision Tree

The Orchestrator uses a 6-point decision tree:

1. **Is security-scoped?** → `security_engineer` (max effort, Fable 5)
2. **Is complexity HIGH and no plan?** → `senior_engineer` (plan first)
3. **Has clear plan?** → `engineer` (execute plan, Haiku)
4. **Otherwise** → `lead_engineer` (complex unplanned work)

## Confidence Scoring Algorithm

**Model Engineer baseline: 0.70**

Adjustments:
- `+0.15` if Quality Engineer score ≥ 85%
- `-0.20` if Quality Engineer score < 60%
- `+0.10` if sample size > 20
- `-0.15` if sample size < 3
- `+0.05` if consistency across tests > 95%

Clamped to `[0.30, 1.00]`

## Quality Gate Decision

All 5 sub-agents run in **parallel** (~20-30ms each):

1. Security Agent: Credential/vulnerability scan
2. Testing Agent: Test coverage & metrics
3. Metrics Agent: System health (p99, error rate)
4. Healing Agent: Config validation
5. Spec Engineer: Spec drift detection (TYPE_A/B/C/D)

**Decision:**
- All 5 PASS → `PROCEED`
- Any ESCALATE → `ESCALATE`

**Latency target:** <30 seconds total

## Spec Drift Types

**TYPE_A:** Documented feature missing in code (breaking regression)
**TYPE_B:** Code feature undocumented in spec (API change risk)
**TYPE_C:** Spec & code mismatch (inconsistent understanding)
**TYPE_D:** Breaking change without deprecation (migration hazard)

## Getting Started

1. **Review the spec**
   ```bash
   cat ../docs/SPEC.md
   ```

2. **Run the example**
   ```bash
   python orchestration/agents/example_end_to_end.py
   ```

3. **Run the tests**
   ```bash
   python orchestration/agents/testing_harness.py
   ```

4. **Execute a task**
   ```python
   from workflow import WorkflowOrchestrator
   
   wf = WorkflowOrchestrator()
   result = wf.execute_task(
       description="Your task",
       scope="Your scope",
       complexity="medium",
       has_plan=True
   )
   ```

5. **View artifacts**
   ```bash
   ls artifacts/2026-04-29/  # DELEGATE-*.yaml, HANDBACK-*.yaml, FEEDBACK-*.yaml
   ```

## Phase 6 Implementation Timeline

- **Week 1 (2026-05-01):** All 8 SDLC agents + testing (46-57 hrs)
- **Week 2 (2026-05-08):** All 5 QG sub-agents + wiring (25-30 hrs)
- **Week 3 (2026-05-15):** 3 feedback loops + integration (20-25 hrs)
- **Week 4 (2026-05-22):** Tuning + documentation (25-30 hrs)

**Total: 116-142 hours**

## References

- Specification: `../docs/SPEC.md`
- Implementation Guide: `../AGENT-IMPLEMENTATION-GUIDE.md`
- Quality Gate Framework: `../QUALITY-GATE-TEST-FRAMEWORK.md`
- Phase 6 Roadmap: `../PHASE-6-IMPLEMENTATION-ROADMAP.md`
- Phase 6 Tasks: `../PHASE-6-TASKS.md`
