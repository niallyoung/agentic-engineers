# Orchestrator — Task Routing

**Role:** Orchestrator (Haiku, low effort)  
**Purpose:** Route incoming tasks to the optimal agent role based on complexity, scope, and characteristics

---

## Overview

Task Routing uses the decision tree from AGENTS.md to assign tasks to specific agent roles, selecting the best model/effort combination.

**Input:** Task description from user, context from codebase  
**Output:** Routing decision with selected role, model, effort level, and DELEGATE markup

**Goal:** Send each task to the agent most likely to complete it with high quality and minimal cost.

---

## Decision Tree

```
Question 1: Is the task scope clear and well-defined?
├─ NO: Too much ambiguity
│  └─ → ESCALATE to human (needs clarification)
│
└─ YES
   │
   Question 2: What is the complexity?
   ├─ Low (straightforward implementation, no ambiguity)
   │  └─ → Engineer (Haiku, high-effort, well-scoped)
   │
   ├─ Medium (some architectural thinking, some ambiguity)
   │  └─ Question 2a: Is the scope fully specified?
   │     ├─ YES (all details provided)
   │     │  └─ → Engineer (Haiku, high-effort)
   │     └─ NO (some requirements unclear)
   │        └─ → Senior Engineer (Sonnet, high-effort, needs to figure out scope)
   │
   └─ High (complex architecture, multi-service impact)
      └─ Question 2b: Does task need architectural design?
         ├─ YES: Cross-service implications, new patterns
         │  └─ → Lead Engineer (Sonnet) or Principal Engineer (Opus)
         │     └─ If cross-service + strategic: Principal (Opus)
         │     └─ If cross-service + tactical: Lead (Sonnet)
         │
         └─ NO: High complexity but single service
            └─ → Senior Engineer (Sonnet, high-effort)
```

---

## Routing Examples

### Example 1: Low-Complexity Feature

**Task Description:**
```
Add Redis caching to {example-service} GetUser endpoint.
Context: Cache key = {userID}, TTL = 1 hour.
Acceptance criteria: Cache hit ratio >80%, no test failures.
```

**Analysis:**
- Scope: Clear ✓ (specific endpoint, known pattern, single service)
- Complexity: Low (caching pattern is established in codebase)
- Well-defined acceptance criteria: Yes ✓

**Routing Decision:**
```
Role: Engineer
Model: Haiku
Effort: high
Confidence: 0.95
Reasoning: Scope is explicit, pattern is known, single service, low complexity
```

### Example 2: Medium-Complexity with Ambiguity

**Task Description:**
```
Refactor {service-name} auth flow. Current flow has too many steps, needs simplification.
Goal: Make login faster and clearer for users.
```

**Analysis:**
- Scope: Somewhat unclear (what counts as "too many steps"? which parts to simplify?)
- Complexity: Medium (involves state management, Cognito integration)
- Requires clarification: Yes (what is "faster"? target: ms improvement? UX metric?)

**Routing Decision:**
```
Role: Senior Engineer
Model: Sonnet
Effort: high
Confidence: 0.80
Reasoning: Medium complexity with scope ambiguity. Sonnet can clarify requirements during implementation.
```

### Example 3: High-Complexity Cross-Service

**Task Description:**
```
Design new event versioning scheme for {example-service} to support schema evolution.
Must support: backward compatibility, migration strategies, and replay safety.
Impacts: {example-service}, {service-name} (consumer), {example-service} (publisher).
```

**Analysis:**
- Scope: Clear ✓ (versioning requirements explicit)
- Complexity: High (cross-service, architectural design required)
- Strategic impact: High (affects event model for all consumers)
- Requires design review: Yes

**Routing Decision:**
```
Role: Principal Engineer
Model: Opus
Effort: high
Confidence: 0.92
Reasoning: Cross-service architectural decision with strategic impact. Requires Principal-level design thinking.
```

### Example 4: Unclear Requirements

**Task Description:**
```
Make the API faster.
```

**Analysis:**
- Scope: Very unclear ✗ (which API? what endpoint? what is "faster"?)
- Complexity: Unknown (could be simple caching, could be major architecture change)
- Must escalate: Yes

**Routing Decision:**
```
Route: ESCALATE to human
Reason: Task scope is too vague. Needs clarification on:
  - Which API endpoint(s)?
  - Current latency vs. target latency?
  - Is this bottleneck identified (profiling data)?
  - Are there constraints (can't change database, etc.)?
```

---

## Routing Criteria

### Route to Engineer (Haiku, high-effort)

If ALL of:
- Complexity ≤ medium
- Scope is explicit and well-bounded
- Task type: feature, bug fix, documentation, test improvement
- Single service (no cross-service coordination)
- Well-known patterns apply
- Acceptance criteria are clear and measurable

### Route to Senior Engineer (Sonnet, high-effort)

If ANY of:
- Complexity = medium-high AND scope somewhat unclear
- Requires significant architectural thinking (but not cross-service)
- Task type: refactor, significant API change, major performance work
- Needs to make design tradeoffs
- Prototype/explore unknown territory within single service

### Route to Lead Engineer (Sonnet, high-effort)

If ANY of:
- Code review task (use code-review skill)
- Cross-service coordination but not strategic
- Need architectural review on well-established patterns
- Technical leadership input needed
- Escalation from Engineer/Senior needing design guidance

### Route to Principal Engineer (Opus, high-effort)

If ANY of:
- Cross-service architecture design required
- Strategic impact (affects >2 services, >1 team)
- New patterns or approaches required
- Significant tradeoff analysis needed (cost vs. complexity vs. performance)
- System-wide consistency concerns

### Route to Security Engineer (Opus, high-effort)

If ANY of:
- Security analysis or threat modeling required
- Authentication/authorization changes
- Data protection or compliance implications
- Third-party integrations with security concerns
- Security incident response

### Escalate to Human

If ANY of:
- Scope is vague or ambiguous
- Requirements unclear
- Success criteria unmeasurable
- Contradictory requirements
- Task is outside system capabilities
- Human decision required (product trade-offs, business priorities)

---

## Effort Level Selection

### High Effort (Recommended for most work)

Use when:
- Task is complex or requires deep thinking
- Error handling/edge cases are critical
- Test coverage must be comprehensive (>80%)
- Documentation of decisions needed
- Risk of rework if rushed

Model: Whatever is assigned (Haiku, Sonnet, Opus)

### Medium Effort (Occasional, well-scoped tasks only)

Use when:
- Task is simple and straightforward
- Error handling is obvious
- Test coverage is straightforward (<80% target acceptable)
- Well-established patterns apply
- Low risk of escalation

Model: Haiku only (Sonnet/Opus always use high-effort)

### Extended Thinking (For very complex tasks)

Enable for:
- First-time implementation of complex pattern
- Significant architectural redesign
- Analysis requiring deep exploration
- High-risk decisions

Model: Sonnet or Opus (Haiku doesn't use extended thinking)

---

## Routing Decision Record

```json
{
  "task_description": "Add Redis caching to {example-service}",
  "routing_decision": {
    "role": "Engineer",
    "model": "claude-haiku-4.5",
    "effort": "high",
    "thinking": "disabled",
    "confidence": 0.95
  },
  "analysis": {
    "scope_clarity": "explicit",
    "complexity_estimate": "low",
    "scope_ambiguity": "none",
    "pattern_familiarity": "established",
    "cross_service": false,
    "strategic_impact": false
  },
  "decision_rationale": "Low-complexity, well-scoped, single-service, established patterns. Haiku is optimal for cost.",
  "alternative_considered": {
    "role": "Senior Engineer",
    "model": "Sonnet",
    "reasoning": "Overkill for this task; only use if scope becomes unclear during implementation."
  }
}
```

---

## Integration with Model Engineer

After task completion and QE verification:

1. **Model Engineer receives feedback** (quality score, tokens, complexity actual vs. estimated)
2. **If complexity was underestimated**, Model Engineer may recommend upgrading similar tasks
3. **Next similar task** uses updated Model Engineer recommendation instead of this routing
4. **Routing rule updated** if pattern is consistent (e.g., "medium-complexity auth = always Sonnet")

---

## Escalation Triggers

If during DELEGATE review or early in execution, discover:
- Scope is actually much larger than estimated → escalate to next level
- Complexity is higher than estimated → escalate to next level
- Cross-service implications discovered → escalate to Lead/Principal
- Security concerns emerge → escalate to Security Engineer
- Architectural questions arise → escalate to Lead/Principal

**Escalation path:** Engineer → Senior → Lead → Principal, or directly to Security if security concern.

---

## Quality Gate Implications

Routing decision affects which quality gates apply:

- **Engineer tasks:** Tier 1 mandatory
- **Senior+ tasks:** Tier 1 + Tier 2 mandatory
- **Lead+ tasks:** Tier 1 + Tier 2 + Tier 3 mandatory
- **Principal/Security tasks:** All Tier 3 checks mandatory

---

## Routing Accuracy Metrics

Monitor monthly:
- % of tasks routed correctly (Quality Engineer assesses post-completion)
- % of tasks that escalated (should be <10%)
- % of rework due to routing error vs. other causes
- Average task duration by route (detect if routing consistently wrong)

If accuracy drops below 90%, review routing criteria with Model Engineer to refine thresholds.
