---
name: Agent Artifacts Repository
description: Storage for DELEGATE/HANDBACK blocks, agent interactions, and intermediate artifacts
type: repository
created: 2026-04-28
---

# Agent Artifacts Repository

Central storage for all DELEGATE/HANDBACK blocks, agent interactions, and work artifacts. Enables:
- **Audit trail**: Complete record of what work was assigned and how agents responded
- **Model comparison**: A/B test different models on same task, compare cost vs quality
- **Continuous improvement**: Feed outcomes back to Model Engineer for iterative refinement
- **Pattern analysis**: Identify reusable patterns, estimate costs, optimize routing

---

## Directory Structure

```
artifacts/
├── README.md (this file)
├── 2026-04-28/
│   ├── DELEGATE-{timestamp}-{task_id}.yaml
│   ├── HANDBACK-{timestamp}-{task_id}.yaml
│   └── ...
├── 2026-05-05/
│   └── ...
└── index.json (metadata index, generated)
```

**Naming Pattern**: `{TYPE}-{TIMESTAMP}-{TASK_ID}.{FORMAT}`

- **TYPE**: DELEGATE or HANDBACK
- **TIMESTAMP**: ISO 8601 (2026-04-28T16:45:00Z)
- **TASK_ID**: kebab-case task identifier
- **FORMAT**: yaml or json

---

## Artifact Contents

### DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: {unique-id}
timestamp: {iso-8601}
from_agent: {Orchestrator}
to_agent: {Engineer/Principal/etc}
role: {from AGENTS.md}
model: {claude-haiku/sonnet/opus}
effort: {low/medium/high/max}
scope: {what to do}
context: {relevant info}
plan: {step-by-step}
success_criteria: {how to know when done}
budget_context: {token usage at delegation time}
---
```

### HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: {matches DELEGATE}
timestamp: {iso-8601}
status: {complete/partial/blocked}
deliverables: {what was created}
tests: {verification results}
tokens_in: {estimated}
tokens_out: {estimated}
model: {actual model used}
effort: {actual effort}
duration_minutes: {wall clock}
escalations: {count}
qe_feedback: {from Quality Engineer if applicable}
  model_assessment: {was model appropriate?}
  reasoning: {why?}
  confidence_for_similar_tasks: {0.0-1.0}
---
```

---

## Future Analysis

### Model Comparison (Phase X)

Example: Compare Opus vs Sonnet on same design task

```bash
# Find all DELEGATEs for same task_id with different models
grep -r "task_id: 2026-04-28-architecture-remediation-week1-design" artifacts/

# Compare:
# - tokens_in / tokens_out (efficiency)
# - quality (from QE feedback)
# - deliverables (completeness)
# - duration_minutes (speed)

# Feed to Model Engineer: "Opus costs 2x, saves 1.5 days → worth it"
```

### Cost Optimization (Phase X)

Use HANDBACK metrics to optimize routing:

```yaml
# Model Engineer learns:
# Haiku (low effort): good for thin validation, bad for design
# Sonnet (high effort): good for implementation, bad for strategic planning
# Opus (high effort): good for complex planning, expensive for simple tasks

# Recommendation: Use Sonnet for Week 2 implementation (not Opus)
```

### Pattern Discovery (Phase X)

Extract reusable patterns from successful HANDBACKs:

```
- "Config Audit Agent works best as Sonnet, high effort, 2-3 hours"
- "Token Advisor Agent should check budget every 30 min, not every change"
- "Quality Gate Orchestrator needs 3000-4000 tokens for aggregation logic"
```

---

## Storage Policy

- **Retention**: Indefinite (these are valuable for learning)
- **Privacy**: No secrets in artifacts (credentials stay in Secrets Manager)
- **Format**: YAML for readability, JSON for tooling
- **Metadata**: Each artifact includes metadata footer with purpose + future use

---

## Integration Points

### Stored By
- Orchestrator (after delegating)
- Quality Engineer (after validating HANDBACK)

### Read By
- Model Engineer (optimization loop)
- Orchestrator (understanding what worked)
- Researchers (pattern analysis)

### Analyzed By
- Model Engineer agent (Phase X: cost vs quality trade-offs)
- Pattern Discovery agent (Phase Y: identify reusable templates)
- Continuous Improvement agent (Phase Z: feedback loops)

---

## Example: Architecture Remediation Artifacts

**Week 1** (Principal designs):
- DELEGATE: Orchestrator → Principal (design 7 agents)
- HANDBACK: Principal → Orchestrator (AGENT-SPECS-WEEK1-DESIGNS.md)

**Week 2** (Engineers implement):
- 7 × DELEGATE: Orchestrator → Engineer (implement one agent each)
- 7 × HANDBACK: Engineers → Orchestrator (agent skill documents)

**Week 3** (Senior refactors):
- DELEGATE: Orchestrator → Senior (refactor hooks + orchestration)
- HANDBACK: Senior → Orchestrator (modified files + tests)

**Week 4** (QE validates):
- DELEGATE: Orchestrator → QE (validate end-to-end)
- HANDBACK: QE → Orchestrator (validation report + audit trail)

**All artifacts stored**: `artifacts/2026-04-28/`, `artifacts/2026-05-05/`, etc.

---

## Future: OpenBrain Integration

Once openbrain concept matures, move beyond artifacts to full context:

```
openbrain/
├── harness-interactions/
│   ├── user-prompt-{id}.md
│   ├── agent-response-{id}.md
│   └── context-{id}.json
├── delegate-handback/
│   └── [current artifact structure]
└── analysis/
    ├── model-comparisons.md
    ├── cost-optimization.md
    └── pattern-library.md
```

This enables:
- Replay any interaction for learning
- A/B test models on real work
- Continuous refinement loop
- Knowledge capture for future agents

---

## Notes

- **Artifacts are not code**: They're metadata + decisions, not source code
- **Artifacts are not logs**: They're structured handoffs, not debugging output
- **Artifacts are valuable**: Every DELEGATE/HANDBACK tells a story about what worked
- **Artifacts are cheap to store**: YAML files, minimal disk space
- **Artifacts drive improvement**: Feed them into Model Engineer optimization loop

---

## Related Documentation

- `agentic-engineers/orchestration/AGENTS.md` — Agent roles and routing
- `agentic-engineers/orchestration/HANDOFF.md` — DELEGATE/HANDBACK protocol
- `agentic-engineers/ARCHITECTURE-AUDIT.md` — Compliance findings
- `agentic-engineers/ARCHITECTURE-REMEDIATION-PLAN.md` — 4-week plan
- `{workspace-name}/TODO.md` — Master project tracking
