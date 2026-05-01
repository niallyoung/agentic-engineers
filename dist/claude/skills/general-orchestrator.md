---
name: General Orchestrator
description: SDLC Orchestrator - Routes all engineering work to optimal specialist agents
type: skill
phase: 6
status: ACTIVE
model: claude-haiku
effort: low
---

# General Orchestrator Skill — SDLC Routing Master

Master orchestrator for ALL software engineering work. Routes tasks to appropriate specialist agents based on complexity, scope, and requirements.

## Quick Start

```bash
# Invoke with a task description
claude-code-skill general-orchestrator \
  --task-type "feature" \
  --scope "Add OAuth2 refresh token rotation to {service-name}" \
  --estimated-complexity "high" \
  --has-plan "false"
```

## Input Parameters

| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `task_type` | string | Yes | "feature", "bugfix", "refactor", "review", "design", "planning", "security" |
| `scope` | string | Yes | Free-form description of the work |
| `context` | string | No | Relevant files, errors, requirements |
| `estimated_complexity` | string | Yes | "low", "medium", "high", "unknown" |
| `has_plan` | boolean | Yes | true/false |
| `is_cross_service` | boolean | No | true/false (affects 2+ repos?) |
| `is_security_scoped` | boolean | No | true/false |

## Routing Decision Tree

```
Task Input
  ↓
[1] Security-scoped? → Security Engineer (Opus)
  ↓ No
[2] Cross-service (2+ repos)? → Principal Engineer (Opus)
  ↓ No
[3] Code review/validation? → Lead Engineer (Sonnet) or Quality Engineer (Sonnet)
  ↓ No
[4] Complex + No plan? → Senior Engineer (Sonnet)
  ↓ No
[5] Well-scoped + Plan? → Engineer (Haiku)
  ↓ No
[6] Scope unclear? → Senior Engineer (Sonnet)
  ↓ Default
    → Engineer (Haiku)
```

## Routing Rules

| Condition | Route | Model | Confidence |
|-----------|-------|-------|------------|
| task_type == "security" | Security Engineer | Opus | 0.95 |
| is_cross_service == true | Principal Engineer | Opus | 0.90 |
| task_type == "review" | Lead Engineer | Sonnet | 0.92 |
| task_type == "validation" \| test/verify keywords | Quality Engineer | Sonnet | 0.90 |
| complexity == "high" AND has_plan == false | Senior Engineer | Sonnet | 0.88 |
| complexity in [medium, low] AND has_plan == true | Engineer | Haiku | 0.93 |
| complexity == "unknown" | Senior Engineer | Sonnet | 0.75 |
| default | Engineer | Haiku | 0.70 |

## Output Format

Returns a routing decision with:
- **routed_agent**: Which specialist should handle this
- **routed_model**: Recommended Claude model
- **confidence**: Confidence in this routing (0.0-1.0)
- **reason**: Why this agent is optimal
- **effort_level**: Expected effort (low/medium/high/max)

## Example: Complex Feature Without Plan

**Input:**
```
task_type: feature
scope: Add OAuth2 refresh token rotation to {service-name}
context: Cognito requires 90-day rolling window per spec
estimated_complexity: high
has_plan: false
is_cross_service: false
is_security_scoped: false
```

**Routing Logic:**
1. Not security-scoped ✗
2. Not cross-service ✗
3. Not review/validation ✗
4. Complex (high) + No plan ✓ → **Senior Engineer**

**Output:**
```yaml
routed_agent: Senior Engineer
routed_model: claude-sonnet
confidence: 0.88
reason: "Complex work without pre-written plan; Senior Engineer will design solution and create plan"
effort_level: high
estimated_tokens: 3000-5000
estimated_duration_seconds: 900-1200
next_steps: "Senior Engineer will receive DELEGATE and create implementation plan before execution"
```

## Example: Well-Scoped Bug Fix with Plan

**Input:**
```
task_type: bugfix
scope: Fix race condition in DynamoDB event consumer
context: Root cause in {service-name}, fix pattern documented, ready to implement
estimated_complexity: medium
has_plan: true
is_cross_service: false
is_security_scoped: false
```

**Routing Logic:**
1. Not security-scoped ✗
2. Not cross-service ✗
3. Not review/validation ✗
4. Complex + No plan ✗
5. Medium complexity + Has plan ✓ → **Engineer**

**Output:**
```yaml
routed_agent: Engineer
routed_model: claude-haiku
confidence: 0.93
reason: "Well-scoped work with existing plan; Haiku efficient for straightforward implementation"
effort_level: high
estimated_tokens: 1500-2500
estimated_duration_seconds: 300-600
next_steps: "Engineer will receive DELEGATE with plan and execute implementation"
```

## Specialist Agents & Responsibilities

| Agent | Model | When | Responsibility |
|-------|-------|------|-----------------|
| **Security Engineer** | Opus | Security-critical work | Threat modeling, vulnerability analysis, access control design |
| **Principal Engineer** | Opus | Cross-service architecture | Design trade-offs, multi-service patterns, long-term scalability |
| **Senior Engineer** | Sonnet | Complex analysis needed | Planning, design review, architecture guidance for unplanned work |
| **Lead Engineer** | Sonnet | Code review | Quality gate, architectural validation, reviewer expertise |
| **Quality Engineer** | Sonnet | Quality validation | Test assessment, coverage analysis, fitness verification |
| **Engineer** | Haiku | Execution | Implement well-scoped, planned work efficiently |

## Confidence Scoring

Confidence reflects routing accuracy based on:
- How clearly the task matches routing criteria (keyword matching, complexity assessment)
- Historical accuracy of similar decisions
- Ambiguity in scope or requirements

**High confidence (0.85+):** Task clearly matches routing rules  
**Medium confidence (0.70-0.85):** Some ambiguity, but reasonable routing  
**Low confidence (<0.70):** Uncertain; may need escalation or clarification

## Escalation Rules

Route to **Senior Engineer** for clarification if:
- Scope is vague ("make it faster", "improve quality")
- Conflicting signals (marked "high complexity" but "has plan")
- New/unfamiliar task type
- Confidence < 0.70

## Integration Points

**Input Sources:**
- Manual user request (via CLI or DELEGATE block)
- CI/CD pipeline (pre-deployment analysis)
- Other agents escalating work (out of their scope)
- Code review requests

**Output Destinations:**
- HANDBACK block written to artifacts/
- Specialist agent receives DELEGATE
- Orchestrator tracks metrics for feedback loop

## Metrics Tracked

After delegating to specialist:
- tokens_used (from sub-agent HANDBACK)
- duration_seconds
- quality_score (0-100, from sub-agent)
- model_efficiency (tokens/quality ratio)
- routing_accuracy (did we route correctly?)

These feed into **Model Engineer** feedback loop for continuous improvement.

## Success Criteria

- ✅ Routes security work with 100% accuracy
- ✅ Routes cross-service to Principal Engineer with 95%+ accuracy
- ✅ Routes complex-unplanned to Senior Engineer with 85%+ accuracy
- ✅ Routes well-scoped to Engineer with 90%+ accuracy
- ✅ Confidence scores are accurate (0.9+ confidence = high accuracy)
- ✅ Escalations appropriately handled
- ✅ Metrics correctly collected and passed to Model Engineer
- ✅ HANDBACK blocks properly formatted
- ✅ Timeout handling (5-10 min waiting for sub-agent response)
- ✅ False routing rate < 10% (corrected by feedback loop)

## Phase 6 Implementation

This skill is the **entry point for full SDLC automation** in Phase 6:

1. ✅ General Orchestrator created (this file)
2. ⏳ Feedback loops designed (Phase 6.1)
3. ⏳ Model Engineer integration (Phase 6.2)
4. ⏳ SDLC agents creation (Phase 7)

**Ready to integrate with:** Engineer, Senior Engineer, Lead Engineer, Security Engineer, Principal Engineer, Quality Engineer agents (coming Phase 7)

---

## Related Documentation

- [AGENTS.md](../AGENTS.md) — Full agent registry
- [general-orchestrator-agent.md](../orchestration/agents/general-orchestrator-agent.md) — Implementation details
- [task-routing.md](orchestration/task-routing.md) — Detailed routing rules
