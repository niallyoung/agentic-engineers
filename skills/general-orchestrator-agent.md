---
name: General Orchestrator Agent Implementation
description: Master routing agent for all software engineering work - directs tasks to optimal agents
type: agent-implementation
phase: 6
status: SPEC_COMPLETE
---

# General Orchestrator Agent — LIVE IMPLEMENTATION

**Role**: Orchestrator (General SDLC)
**Model**: claude-haiku-4-5
**Effort**: low
**Purpose**: Route ALL engineering work to most appropriate agent based on task complexity, scope, and requirements

---

## Agent Logic

```
WHEN engineering work arrives (commit work, feature request, bug, refactor):

INPUT: DELEGATE block with:
  - task_type: "feature" | "bugfix" | "refactor" | "review" | "design" | "planning"
  - scope: free-form description
  - context: relevant files, errors, requirements
  - estimated_complexity: "low" | "medium" | "high" | "unknown"
  - has_plan: true | false

PROCESS:

  1. ANALYZE task characteristics
     - Is this security-scoped? (credentials, auth, access control)
     - Does it need cross-service architecture? (affects 2+ repos)
     - Is it complex coding without pre-written plan?
     - Is it code review or quality verification?
     - Is it well-scoped with a written plan?
  
  2. APPLY routing rules (in order):
     
     IF task_type == "security" OR scope contains security keywords:
       ROUTE: Security Engineer (Opus)
       REASON: "Security-critical work requires maximum model"
       CONFIDENCE: 0.95
     
     ELIF task needs cross-service architecture:
       ROUTE: Principal Engineer (Opus)
       REASON: "Cross-service decisions require architectural expertise"
       CONFIDENCE: 0.90
     
     ELIF task_type == "review" OR task contains "review" OR task contains "code review":
       ROUTE: Lead Engineer (Sonnet)
       REASON: "Code review and architectural guidance"
       CONFIDENCE: 0.92
     
     ELIF task_type == "validation" OR task contains "test" OR task contains "verify":
       ROUTE: Quality Engineer (Sonnet)
       REASON: "Quality verification and validation"
       CONFIDENCE: 0.90
     
     ELIF estimated_complexity == "high" AND has_plan == false:
       ROUTE: Senior Engineer (Sonnet)
       REASON: "Complex work without plan; need planning + execution"
       CONFIDENCE: 0.88
     
     ELIF estimated_complexity in ["medium", "low"] AND has_plan == true:
       ROUTE: Engineer (Haiku)
       REASON: "Well-scoped, planned work; Haiku sufficient"
       CONFIDENCE: 0.93
     
     ELIF estimated_complexity == "unknown":
       ROUTE: Senior Engineer (Sonnet)
       REASON: "Uncertain scope; Senior Engineer can assess and plan"
       CONFIDENCE: 0.75
     
     ELSE:
       ROUTE: Engineer (Haiku)
       REASON: "Default to Engineer; escalate if insufficient"
       CONFIDENCE: 0.70

  3. CREATE sub-DELEGATE block
     ```yaml
     ---
     handoff_type: DELEGATE
     task_id: {task_id}
     parent_task_id: {original_orchestrator_task_id}
     timestamp: {iso8601}
     role: {routed_role}
     model: {recommended_model}
     effort: {effort_level}
     scope: {task_scope}
     context: {full_context}
     plan: {if_exists}
     routing_reason: {why_this_agent}
     confidence: {0.0-1.0}
     ---
     ```

  4. DELEGATE to routed agent
     Write sub-DELEGATE to artifacts/
     Wait for HANDBACK (10-min timeout for simple, 30-min for complex)

  5. RECEIVE HANDBACK from sub-agent
     - Extract: status, deliverables, tokens_used, quality_score, escalations
     - Record metrics: model, effort, outcome

  6. [ASYNC] Notify Model Engineer (feedback loop)
     - Pass: sub-agent HANDBACK + metrics
     - Task: Analyze efficiency, recommend model/effort for next similar task

  7. RETURN final HANDBACK to original requester
     ```yaml
     ---
     handoff_type: HANDBACK
     task_id: {original_task_id}
     timestamp: {iso8601}
     status: complete
     routed_agent: {agent_name}
     routed_model: {model}
     sub_task_handback: {sub-agent HANDBACK}
     metrics:
       tokens_used: {total}
       duration_seconds: {time}
       model_efficiency: {0.0-1.0}
       quality_score: {0-100}
     recommendation: "Work completed by {agent}, quality {score}/100"
     ---
     ```

  8. WRITE OpenTelemetry span
     - span_name: "general-orchestrator-routing"
     - attributes: task_type, routed_agent, model, confidence
     - event: {name: "routing_decision", attributes: {reason}}
```

---

## Routing Decision Tree

```
Task arrives at Orchestrator
         ↓
[1] Is it security-scoped?
    YES → Security Engineer (Opus, max effort)
    NO  → Continue to [2]
         ↓
[2] Does it affect 2+ services?
    YES → Principal Engineer (Opus, high effort)
    NO  → Continue to [3]
         ↓
[3] Is it code review or validation?
    YES → Lead Engineer (Sonnet, high effort) for review
    NO  → Quality Engineer (Sonnet, medium) if testing-focused
         ↓
[4] Is it complex work without a plan?
    YES → Senior Engineer (Sonnet, high effort)
    NO  → Continue to [5]
         ↓
[5] Is it well-scoped with a plan?
    YES → Engineer (Haiku, high effort)
    NO  → Continue to [6]
         ↓
[6] Scope unclear?
    YES → Senior Engineer (Sonnet, high effort, to assess first)
    NO  → Engineer (Haiku, high effort, default)
```

---

## Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-02-orchestrator-add-auth-{service-name}
timestamp: 2026-06-02T09:00:00Z
role: General Orchestrator
model: claude-haiku-4-5
effort: low
scope: >
  Route engineering work for {service-name} service.
  Add OAuth2 refresh token rotation per Cognito best practices.
context:
  - Service: {service-name} (Go/Lambda)
  - Task type: feature
  - Estimated complexity: high (OAuth2 state machine)
  - Has plan: false
  - Relevant files: lambda/auth/main.go, lambda/auth/oauth.go
  - Requirements: Per spec, must support 90-day rolling window
estimated_complexity: high
has_plan: false
---
```

---

## Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-orchestrator-add-auth-{service-name}
timestamp: 2026-06-02T09:35:00Z
status: complete
routed_agent: Senior Engineer
routed_model: claude-sonnet-4-6
routing_decision:
  reason: "Complex work without pre-written plan"
  confidence: 0.88
sub_task_handback:
  status: complete
  deliverables:
    - Added: lambda/auth/oauth_rotation.go (refresh token rotation logic)
    - Modified: lambda/auth/main.go (wire into handler)
    - Added: lambda/auth/oauth_rotation_test.go (unit tests)
  tokens_used: 3200
  duration_seconds: 420
  quality_score: 92
  notes: "Plan was written first (10 min), then implementation (7 min). Complex state machine, but Senior Engineer handled well."
metrics:
  total_tokens: 3200
  total_duration_seconds: 420
  model: sonnet
  effort: high
  model_efficiency: 0.85
  quality_score: 92
recommendation: "Work routed correctly. Senior Engineer executed well on complex, unplanned work. Quality 92/100. Ready for review."
---
```

---

## Routing Rules (Reference)

| Task Type | Complexity | Has Plan | Route | Model | Effort |
|-----------|-----------|----------|-------|-------|--------|
| Security | Any | Any | Security Engineer | Opus | max |
| Cross-service | Any | Any | Principal Engineer | Opus | high |
| Code review | Any | Any | Lead Engineer | Sonnet | high |
| Testing/Validation | Any | Any | Quality Engineer | Sonnet | medium |
| Feature | High | No | Senior Engineer | Sonnet | high |
| Feature | High | Yes | Engineer | Haiku | high |
| Feature | Medium | No | Senior Engineer | Sonnet | high |
| Feature | Medium | Yes | Engineer | Haiku | high |
| Feature | Low | Yes | Engineer | Haiku | high |
| Bug fix | High | No | Senior Engineer | Sonnet | high |
| Bug fix | Medium | Yes | Engineer | Haiku | high |
| Refactor | High | No | Senior Engineer | Sonnet | high |
| Refactor | Medium | Yes | Engineer | Haiku | high |
| Unknown | Any | No | Senior Engineer | Sonnet | high |

---

## Integration Points

**Invoked From**:
- Manual user request (via DELEGATE block)
- CI/CD pipeline (for automated workflows)
- Other agents escalating (when work is out of scope)

**Invokes** (via sub-DELEGATE):
- Security Engineer (Opus)
- Principal Engineer (Opus)
- Senior Engineer (Sonnet)
- Lead Engineer (Sonnet)
- Quality Engineer (Sonnet)
- Engineer (Haiku)

**Feedback Loop**:
- Model Engineer analyzes routing accuracy + token efficiency
- Recommendations update confidence scores
- Next similar task uses refined routing decision

---

## Success Criteria

- ✅ Routes security work to Security Engineer (100% accuracy)
- ✅ Routes cross-service to Principal Engineer (95%+ accuracy)
- ✅ Routes code review to Lead Engineer or Quality Engineer (90%+ accuracy)
- ✅ Routes complex unplanned work to Senior Engineer (85%+ accuracy)
- ✅ Routes well-scoped work to Engineer (90%+ accuracy)
- ✅ HANDBACK includes routing decision + confidence
- ✅ Sub-agent HANDBACK captured correctly
- ✅ Metrics tracked (tokens, duration, quality)
- ✅ OpenTelemetry spans created
- ✅ Timeout handling (escalate if sub-agent doesn't respond)
- ✅ False routing <10% (Model Engineer feedback corrects over time)
