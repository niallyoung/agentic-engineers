# Agent Creation Guide

This guide explains how to create new agent roles in the Agentic Engineers framework.

## Overview

Agents are specialized roles that handle specific types of tasks in the framework. Each agent has:
- A **canonical model tier** (Haiku, Sonnet, or Opus)
- A **thinking mode** (on/off) based on whether the task requires judgment
- An **effort level** (low, medium, high, max) indicating reasoning depth
- A **system prompt** defining its behavior and decision-making logic

## Quick Start

Use the `agent-creator` skill to scaffold a new agent:

```bash
python3 scripts/agent-creator.py --role "data-engineer" --model "claude-sonnet-4.6" --effort high
```

This generates:
- `src/agents/data-engineer/AGENT.md` — Agent specification
- `src/agents/data-engineer/SYSTEM.md` — System prompt
- `tests/agents/test_data_engineer.py` — Test scaffolds

## Agent Structure

### 1. Agent Specification (`AGENT.md`)

Every agent has a frontmatter block defining its metadata:

```yaml
---
role: data-engineer
canonical_model: claude-sonnet-4.6
thinking: true
effort: high
cost_per_task: $0.09
purpose: >
  Data pipeline design, ETL optimization, database schema design
---
```

**Fields:**
- `role` — Unique identifier (kebab-case)
- `canonical_model` — Claude model tier (haiku, sonnet, opus)
- `thinking` — Enable extended thinking (true/false)
- `effort` — Reasoning depth (low, medium, high, max)
- `cost_per_task` — Estimated cost per invocation
- `purpose` — One-line description of agent's role

### 2. System Prompt (`SYSTEM.md`)

The system prompt defines the agent's behavior. It should include:

```markdown
# Data Engineer Agent

**Role**: Data Engineer
**Model**: claude-sonnet-4.6
**Effort**: high
**Purpose**: Data pipeline design, ETL optimization, database schema design

---

## Agent Logic

```
WHEN Data Engineer receives DELEGATE for data-related tasks:

INPUT: DELEGATE block with:
  - scope: Data pipeline or database design task
  - context: Requirements, constraints, existing schema
  - has_plan: varies (Data Engineer can plan or execute)

PROCESS:
  1. ANALYZE requirements
  2. DESIGN data model or pipeline
  3. IMPLEMENT (if has_plan=true) or DELEGATE (if complex)
  4. MEASURE quality and metrics
  5. RETURN HANDBACK
```

## Decision Rule

When to execute vs. escalate:
- ✅ Execute: Standard schema design, ETL pipeline setup
- ⚠️ Escalate to Principal Engineer: Multi-service data architecture
- ⚠️ Escalate to Security Engineer: PII/sensitive data handling
```

### 3. Provider Mapping (`src/config/models.yaml`)

Add your agent to the model mapping:

```yaml
data_engineer:
  canonical: "claude-sonnet"
  thinking: true
  providers:
    claude: "claude-sonnet-4.6"
    copilot: "gpt-4-turbo"
    openai: "gpt-4-turbo"
    google: "gemini-1-5-pro"
    meta: "llama-3-70b"
```

## Thinking Mode Decision

**Enable thinking (true) when:**
- Task requires judgment or trade-off analysis
- Multiple valid approaches exist
- Output depends on complex reasoning
- Subtle errors would be costly

**Disable thinking (false) when:**
- Task is deterministic (routing, execution of pre-planned work)
- Output follows a fixed rule or checklist
- Speed and cost matter more than deep reasoning

See [docs/ARCHITECTURE.md](../ARCHITECTURE.md) for the full thinking mode rationale.

## Effort Level Guidelines

| Effort | Token Budget | Use Case |
|--------|--------------|----------|
| **Low** | 500-1,000 | Routing, simple lookups, deterministic tasks |
| **Medium** | 1,000-3,000 | Planning, validation, moderate analysis |
| **High** | 3,000-10,000 | Complex design, multi-step reasoning, reviews |
| **Max** | 10,000+ | Architecture, security analysis, unconstrained exploration |

## Testing Your Agent

### 1. Unit Tests

```python
# tests/agents/test_data_engineer.py
import pytest
from src.agents.data_engineer import DataEngineerAgent

def test_data_engineer_routes_correctly():
    agent = DataEngineerAgent()
    task = "Design a user activity tracking schema"
    result = agent.process(task)
    assert result["status"] == "success"
    assert result["quality_score"] >= 90
```

### 2. Integration Tests

```bash
# Test via orchestrator
opencode --agent orchestrator "Design a user activity tracking schema"
# Should route to Data Engineer
```

### 3. Validation

```bash
# Run agent validator
python3 scripts/validate-agent.py data-engineer
# Checks:
# - AGENT.md frontmatter valid
# - SYSTEM.md exists
# - Provider mapping exists
# - Tests pass
```

## Adding to Orchestrator Routing

Edit `src/agents/orchestrator/SYSTEM.md` to add routing logic:

```markdown
### Data Tasks
- Schema design → Data Engineer
- ETL pipeline → Data Engineer
- Database optimization → Data Engineer
- Multi-service data architecture → Principal Engineer (escalate)
```

## Examples

### Example 1: Simple Agent (Deterministic)

```yaml
---
role: formatter
canonical_model: claude-haiku-4.5
thinking: false
effort: low
cost_per_task: $0.03
purpose: Code formatting and linting
---
```

**Rationale:** Formatting is deterministic. No thinking needed.

### Example 2: Judgment-Heavy Agent

```yaml
---
role: product-engineer
canonical_model: claude-opus-4.8
thinking: true
effort: high
cost_per_task: $0.15
purpose: Product requirements analysis, feature prioritization
---
```

**Rationale:** Product decisions require deep judgment and trade-off analysis.

## Best Practices

1. **Single Responsibility** — Each agent should have one clear purpose
2. **Clear Escalation Paths** — Define when to escalate to higher-tier agents
3. **Measurable Success Criteria** — Include quality thresholds in HANDBACK
4. **Provider Compatibility** — Test on all supported harnesses
5. **Documentation** — Write clear examples and decision rules

## Troubleshooting

### Agent not routing correctly

**Symptom:** Orchestrator doesn't route to your new agent.

**Fix:**
1. Check `src/agents/orchestrator/SYSTEM.md` has routing rule
2. Verify agent name matches in `src/config/models.yaml`
3. Run `make install` to regenerate harness configs

### Model not found

**Symptom:** `Error: Model 'your-model' not found`

**Fix:**
1. Check `src/config/models.yaml` has provider mapping
2. Verify model name is correct for your harness
3. Run `make install-{harness}` to regenerate

### Quality scores too low

**Symptom:** Agent consistently returns quality < 90

**Fix:**
1. Review success criteria in SYSTEM.md
2. Consider enabling thinking mode
3. Upgrade to higher-tier model (Sonnet → Opus)

## Next Steps

- [Skill Creation Guide](skill-creation.md)
- [Harness Setup](harness-setup/)
- [Testing Guide](troubleshooting.md)
