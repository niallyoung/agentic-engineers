# Architecture Integration Guide

How AGENTS.md, SKILLS.md, QUEUE-PROTOCOL.md, and HANDOFF.md work together as a cohesive system.

---

## Document Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│ AGENTS.md                                                       │
│ WHO: Role assignments (Engineer, Senior Engineer, etc.)        │
│ ROUTING: Decision tree for which agent handles which task      │
│ CONSTRAINTS: Mandatory rules (Red-Green TDD, queue-based)      │
└─────────────────────────────────────────────────────────────────┘
            ↓ Each role has...
┌─────────────────────────────────────────────────────────────────┐
│ SKILLS.md                                                       │
│ WHAT: Specific skills and workflows for each role              │
│ HOW: Step-by-step procedures (Red-Green TDD phases, etc.)      │
│ WHEN: Escalation rules (when to promote to next role)          │
└─────────────────────────────────────────────────────────────────┘
            ↓ Work flows through...
┌─────────────────────────────────────────────────────────────────┐
│ QUEUE-PROTOCOL.md                                               │
│ WORKFLOW: Active queue system (incoming → processing → done)   │
│ ORCHESTRATOR LOOP: 30-60s polling, routing, decision-making    │
│ ARTIFACTS: DELEGATE storage, HANDBACK processing, feedback     │
└─────────────────────────────────────────────────────────────────┘
            ↓ Using structured format...
┌─────────────────────────────────────────────────────────────────┐
│ HANDOFF.md                                                      │
│ FORMAT: DELEGATE/HANDBACK/FEEDBACK block structure             │
│ RED-GREEN TDD: Evidence requirements, rejection rules          │
│ QUALITY GATES: Tier 1/2/3 checklists, QE feedback             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example: Complete Task Lifecycle

### Step 1: Task Arrives

User creates request in `artifacts/queue/incoming/`:

```yaml
task_id: 2026-04-30-fix-token-timeout
description: "Fix token validation timeout in {service-name}"
priority: "high"
```

### Step 2: Orchestrator Routes (AGENTS.md Decision Tree)

Orchestrator polls `incoming/` every 30-60 seconds:

```
1. Is task security-scoped? NO
2. Is task cross-service? NO
3. Is task complex coding without plan? NO (Lead Engineer will diagnose)
4. Is task code review? NO
5. Is task well-planned, low-medium? NO (needs diagnosis first)
6. ROUTE TO: Lead Engineer (to diagnose and write plan)
```

**Applies AGENTS.md:**
- Role: Lead Engineer (claude-sonnet-4-6)
- Effort: high
- Model from AGENTS.md routing table

### Step 3: Orchestrator Creates DELEGATE (HANDOFF.md Format)

```yaml
handoff_type: DELEGATE
task_id: 2026-04-30-fix-token-timeout
role: Lead Engineer
model: claude-sonnet-4-6
effort: high
red_green_tdd_required: false  # Diagnosis, not code change
plan:
  1. Reproduce the bug
  2. Trace through code to find root cause
  3. Document findings and recommended fix
  4. (No implementation yet)
```

**Stored in:** `artifacts/delegates/2026-04-30/DELEGATE-...yaml`  
**Agent receives:** DELEGATE block + pointer to SKILLS.md

### Step 4: Lead Engineer Executes (SKILLS.md > Lead Engineer Skills)

Lead Engineer reads SKILLS.md section "Lead Engineer Skills > Root Cause Analysis":

```
1. Reproduce: Create minimal test case
2. Trace: Follow code flow to identify where assumption breaks
3. Evidence: Point to specific line numbers
4. Hypothesis: Root cause with evidence
5. Options: Possible fixes with tradeoffs
```

Lead Engineer completes diagnosis and returns HANDBACK:

```yaml
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: complete
red_green_tdd_applied: false  # No code changes
deliverables:
  - Root cause: Client-side clock skew
  - Evidence: lambda/api/main.go:92 checks time.Now() vs token exp
  - Options: Add grace period OR sync clocks
  - Recommended: Add grace period (simpler, lower-risk)
```

**Stored in:** `artifacts/queue/processing/{task_id}-HANDBACK-Lead-Engineer.yaml`

### Step 5: Orchestrator Re-Routes (QUEUE-PROTOCOL.md Active Loop)

Orchestrator polls `processing/` and finds HANDBACK from Lead Engineer:

```python
if handback.status == "complete":
    # Diagnosis done; now create implementation task
    # Route to Engineer with concrete plan
    engineer_delegate = create_delegate(
        role="Engineer",
        plan=handback.options[0],  # "Add grace period"
        red_green_tdd_required=True  # Now we're changing code
    )
    send_to_queue_incoming(engineer_delegate)
```

### Step 6: Engineer Executes (SKILLS.md > Engineer Skills > Red-Green TDD)

Engineer receives DELEGATE with `red_green_tdd_required: true` and `plan` with RED-GREEN-REFACTOR phases.

Engineer reads SKILLS.md "Engineer Skills > Red-Green TDD":

```
1. RED Phase: Write failing test
   - Name: TestTokenExpiryGracePeriod
   - Assert: Token 25s expired is still accepted
   - Run: Verify it fails
   
2. GREEN Phase: Minimal implementation
   - Change: Modify line 92 to accept grace period
   - Run: Verify test passes
   
3. REFACTOR Phase: Improve without changing behavior
   - Extract: grace period to constant
   - Improve: error messages
   
4. VERIFY: Run full test suite
```

Engineer executes plan and returns HANDBACK with evidence:

```yaml
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: complete
red_green_tdd_applied: true
red_green_evidence:
  - "[RED] TestTokenExpiryGracePeriod added, FAILS"
  - "[GREEN] Modified line 92, test PASSES"
  - "[REFACTOR] Extracted GRACE_PERIOD_SECS constant"
  - "[VERIFY] All 47 tests pass, coverage 89%"
tests:
  - "make verify": PASS
```

### Step 7: Quality Engineer Verifies (SKILLS.md > Quality Engineer Skills)

Quality Engineer receives HANDBACK and reads SKILLS.md "Quality Engineer Skills > Quality Gate Verification":

**Tier 1 Checklist:**
- [ ] Tests pass? YES (47 tests)
- [ ] Coverage maintained? YES (89%, was 87%)
- [ ] Lint passes? YES
- [ ] Red-Green TDD applied? YES (evidence shows all phases)
- [ ] No production hazards? YES

**Tier 2 Checklist** (applies to Engineer):
- [ ] Test coverage ≥85%? YES (89%)
- [ ] No new exported symbols without docs? N/A (no new exports)
- [ ] Plan completeness? YES (all steps executed)

**Verdict:** PASS ✓

Quality Engineer adds feedback:

```yaml
qe_feedback:
  tier_1_verdict: PASS
  red_green_tdd_applied: true
  model_assessment: "haiku_suitable"
  confidence_for_similar_tasks: 0.94
```

### Step 8: Orchestrator Decides Next Step (QUEUE-PROTOCOL.md Fast-Track)

Quality Engineer moved task to `artifacts/queue/done/{task_id}-complete.yaml`.

Orchestrator polls `done/` and checks FAST-TRACK criteria:

```
✓ All 5 quality gates PASS
✓ Tests: PASS, coverage maintained
✓ No escalations, no rejections
✓ Red-Green TDD applied with clear evidence
✓ Scope is Tier 1 (low-risk change)

DECISION: PROCEED → Auto-merge to main (no human review needed)
```

### Step 9: Model Engineer Analyzes (SKILLS.md > Model Engineer Skills)

After task completes, Model Engineer analyzes QE feedback:

```
Task type: Bug fix (simple scope)
Assigned model: Haiku (claude-haiku-4-5)
QE verdict: PASS, haiku_suitable, confidence 0.94
Tokens used: 2020 (estimate: 1200 in + 820 out)
Efficiency: High (well-scoped plan, no rework)

Finding: For simple bug fixes with clear plan, Haiku works 94% of the time.
Recommendation: Continue using Haiku for next similar "bug fix (simple)" task
Confidence: 0.94
```

**Stored in:** `artifacts/feedback/model-recommendations.jsonl`

### Step 10: Next Similar Task Benefits

Next task arrives: "Fix typo in constant" (bug fix, simple).

Orchestrator checks Model Engineer recommendations:

```python
recommendations = load_json("artifacts/feedback/model-recommendations.jsonl")
match = find_recommendation(task_type="bug_fix_simple")
if match and match.confidence > 0.85:
    model = match.recommended_model  # "claude-haiku-4-5"
    effort = match.recommended_effort  # "high"
```

Orchestrator routes to Haiku (as recommended) instead of trying Sonnet.

**System improves over time through feedback loops.**

---

## Key Integration Points

### 1. AGENTS.md → QUEUE-PROTOCOL.md

**AGENTS.md specifies:**
- Role assignments (who does what)
- Model choices (Haiku, Sonnet, Opus)
- Routing decision tree

**QUEUE-PROTOCOL.md implements:**
- Orchestrator active loop (uses routing tree)
- Queue transitions (incoming → processing → done)
- Fast-track criteria (auto-merge for low-risk)

**Connection:** Orchestrator reads AGENTS.md decision tree when polling `incoming/`.

### 2. AGENTS.md → SKILLS.md

**AGENTS.md says:**
- "Engineer does well-scoped implementation with pre-written plan"

**SKILLS.md details:**
- "Engineer SKILL 1: Red-Green TDD (mandatory for code changes)"
- "Engineer SKILL 2: Error Handling (must never panic)"
- "Engineer SKILL 3: Code Quality Checklist (lint, tests, coverage)"

**Connection:** Engineer receives DELEGATE, reads SKILLS.md to execute.

### 3. SKILLS.md → HANDOFF.md

**SKILLS.md specifies:**
- "Red-Green TDD: Write failing test → implement fix → refactor → verify"

**HANDOFF.md requires:**
- `red_green_evidence: [...]` array showing each phase with line numbers
- Quality Engineer rejection rule: "If RED phase missing → REJECT"

**Connection:** Engineer documents evidence in HANDBACK format specified by HANDOFF.md.

### 4. QUEUE-PROTOCOL.md → HANDOFF.md

**QUEUE-PROTOCOL.md says:**
- Store DELEGATE in `artifacts/delegates/`
- Store HANDBACK in `artifacts/queue/processing/`
- Move to `artifacts/queue/done/` after QE verification

**HANDOFF.md specifies:**
- Exact format of DELEGATE and HANDBACK blocks
- `delegate_artifact: "path/to/DELEGATE"` reference in HANDBACK
- QE feedback block structure

**Connection:** All artifacts follow HANDOFF.md format; queue system manages file locations.

### 5. SKILLS.md → Quality Engineer Feedback Loop

**Quality Engineer SKILL:**
- "Verify Red-Green TDD evidence (RED, GREEN, REFACTOR, VERIFY all present)"
- "Assess model suitability: was this model appropriate for task?"
- "Add feedback for Model Engineer"

**Model Engineer SKILL:**
- "Analyze QE feedback to identify patterns"
- "Generate recommendations for next similar task"
- "Build confidence scores (0.0–1.0)"

**Connection:** QE feedback feeds directly into Model Engineer recommendations.

---

## Mandatory Enforcement Points

| Rule | Source | Enforcer | Action |
|------|--------|----------|--------|
| All work via queue system | QUEUE-PROTOCOL.md | Orchestrator | Routes through `incoming/processing/done/` |
| Red-Green TDD for code changes | AGENTS.md constraint | Quality Engineer | REJECT if evidence missing |
| Plan required for Engineer | AGENTS.md constraint | Orchestrator | Don't create DELEGATE without plan |
| Tier 1 checklist | SKILLS.md | Quality Engineer | REJECT if tests fail or coverage drops |
| Model assessment feedback | SKILLS.md | Quality Engineer | REJECT if qe_feedback missing |
| No Orchestrator direct execution | AGENTS.md constraint | (Self-enforcing) | Orchestrator only routes; never edits code |
| DELEGATE artifact stored | QUEUE-PROTOCOL.md | Orchestrator | Store before sending to agent |

---

## File Locations Summary

| Artifact Type | Path | Created By | Used By |
|---|---|---|---|
| DELEGATE | `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator | Agent (executes); Orchestrator (ref) |
| HANDBACK | `artifacts/queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent | Quality Engineer (verifies) |
| QE Feedback | (appended to HANDBACK) | Quality Engineer | Model Engineer (analyzes) |
| Final Decision | `artifacts/queue/done/{task_id}-{status}.yaml` | Orchestrator | Orchestrator (decision: PROCEED/REWORK/ESCALATE) |
| Model Recommendations | `artifacts/feedback/model-recommendations.jsonl` | Model Engineer | Orchestrator (applies for next task) |
| Archive | `artifacts/archive/YYYY-MM-DD/{task_id}/*` | Orchestrator | Historical queries, pattern analysis |

---

## Decision Flowchart

```
New task arrives in artifacts/queue/incoming/
    ↓
Orchestrator reads task and applies AGENTS.md routing rules
    ├─ Security-scoped? → Security Engineer
    ├─ Cross-service? → Principal Engineer
    ├─ Complex without plan? → Senior Engineer (write plan first)
    ├─ Code review/QA? → Lead Engineer or Quality Engineer
    └─ Well-planned, simple? → Engineer
    ↓
Orchestrator creates DELEGATE (HANDOFF.md format)
  - Includes plan with RED-GREEN-REFACTOR phases (if code change)
  - Stores in artifacts/delegates/YYYY-MM-DD/
  - Moves task to artifacts/queue/processing/
    ↓
Agent receives DELEGATE, reads SKILLS.md for role-specific guidance
    ↓
Agent executes work per plan, documents in HANDBACK
  - If code change: includes red_green_evidence array
  - If blocked: status=blocked, escalation reason
  - Stores in artifacts/queue/processing/
    ↓
Orchestrator polls processing/, finds HANDBACK
    ↓
Routes to Quality Engineer (if status=complete) OR Senior Engineer (if status=blocked)
    ↓
Quality Engineer verifies Tier 1/2 checklist
  - Verify tests pass, coverage maintained
  - Verify Red-Green TDD evidence present
  - Verify no security/hazards
    ↓
    ├─ If PASS: Add qe_feedback, move to artifacts/queue/done/{task_id}-complete.yaml
    │   ↓
    │   Orchestrator checks FAST-TRACK criteria
    │   ├─ If eligible: Auto-merge to main
    │   └─ Otherwise: Notify human for review
    │
    └─ If FAIL: status=rejected, move to artifacts/queue/done/{task_id}-rejected.yaml
        ↓
        Orchestrator creates new DELEGATE with rejection reason
        ↓
        Task returns to artifacts/queue/incoming/ for rework
        ↓
        (After 3 rejections, escalate to Senior Engineer for diagnosis)
```

---

## Summary

This architecture creates a **closed-loop, self-improving system**:

1. **AGENTS.md** defines who does what and how work is routed
2. **SKILLS.md** defines how each role executes their work
3. **QUEUE-PROTOCOL.md** automates the workflow with active orchestration
4. **HANDOFF.md** standardizes the format of all work artifacts
5. **Feedback loops** improve routing for future similar tasks

**Red-Green TDD** is enforced at every code change, ensuring quality from day one.
**Active queue management** ensures work flows smoothly and escalations are handled automatically.
**Quality Engineer gatekeeping** ensures only good code passes through.
**Model Engineer optimization** continuously improves efficiency.

The system is platform-independent (works with any agent/model), self-contained (no external dependencies), and designed to be automated (Orchestrator active loop requires minimal human intervention).

