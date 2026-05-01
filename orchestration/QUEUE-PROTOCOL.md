# Queue-Based Workflow Protocol

Active orchestration model where the Orchestrator continuously monitors `incoming/`, `processing/`, and `done/` queues to coordinate agent work and enforce workflow discipline.

---

## Queue Structure

```
artifacts/
├── queue/
│   ├── incoming/          # New work, ready for Orchestrator routing
│   ├── processing/        # Work assigned to agent, awaiting HANDBACK
│   └── done/              # Completed work, ready for review/escalation
├── delegates/             # DELEGATE artifacts (stored for reference)
├── feedback/              # Feedback loops (model recommendations, patterns)
└── archive/               # Historical (date-keyed, searchable)
```

---

## Artifact Lifecycle

### 1. DELEGATE (Stored Immediately)

When Orchestrator creates a DELEGATE block:

**Store as:** `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-30-fix-token-timeout
role: Engineer
model: claude-haiku-4-5
effort: high
scope: "Fix token validation timeout in {service-name}; do not change Cognito config"
red_green_tdd_required: true  # NEW: Signals Engineer must start with failing test
context: [...]
success_criteria: [...]
plan: [...]
---
```

**Metadata:**
- `red_green_tdd_required: true/false` — Does this task mandate Red-Green TDD?
  - **true** for: bugs, feature implementation, refactoring, any code change
  - **false** for: pure analysis, documentation-only, review tasks
- Stored at creation time (before sending to agent)

### 2. HANDBACK (Full Lifecycle)

When agent completes work:

**Input DELEGATE must be available.**  
Agent reads from: `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-*.yaml`

**Output HANDBACK stored as:** `artifacts/queue/processing/{task_id}-HANDBACK.yaml`

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: complete | blocked | partial | rejected  # NEW: rejected for QE failures
delegate_artifact: "delegates/2026-04-30/DELEGATE-2026-04-30-fix-token-timeout-Engineer.yaml"
deliverables: [...]
tests: [...]
red_green_tdd_applied: true  # NEW: Did agent follow Red-Green TDD?
red_green_evidence:          # NEW: Proof of Red-Green cycle
  - "Added TestTokenTimeout (RED) at line 120"
  - "Implemented fix at line 92 (GREEN)"
  - "Refactored error handling (REFACTOR)"
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4-5
effort: high
duration_minutes: 18
escalations: 0
---
```

**Status Values:**
- `complete` — All success_criteria met, ready for QE review
- `partial` — Some success_criteria met, deferred items documented
- `blocked` — Cannot proceed, needs unblocking (escalate to Senior Engineer)
- `rejected` — QE rejected; send back to Engineer for rework (see Rejection Loop, below)

### 3. Queue Transitions

```
incoming/{task_id}-NEW.yaml
    ↓ (Orchestrator assigns)
processing/{task_id}-HANDBACK.yaml
    ↓ (Quality Engineer verifies)
done/{task_id}-{status}.yaml
    ↓ (Orchestrator decides next step)
    ├─ PROCEED → merge/deploy
    ├─ REWORK → send new DELEGATE back to incoming/
    └─ ESCALATE → promote to Senior Engineer or Lead
```

**File Naming in Queue:**
- `incoming/` — `{task_id}-NEW.yaml` (stores Orchestrator's initial request)
- `processing/` — `{task_id}-HANDBACK-{role}.yaml` (agent's response)
- `done/` — `{task_id}-{final_status}.yaml` (after QE decision)

---

## Orchestrator Active Loop

The Orchestrator runs **every 30–60 seconds**:

```python
def orchestrator_loop():
    while True:
        # 1. Check incoming/ for new work
        incoming = list_files("artifacts/queue/incoming/")
        for task_file in incoming:
            task = load_yaml(task_file)
            delegate = create_delegate(task)
            send_to_agent(delegate)
            move(task_file, f"processing/{task_id}-NEW.yaml")
        
        # 2. Check processing/ for completed work
        processing = list_files("artifacts/queue/processing/")
        for handback_file in processing:
            handback = load_yaml(handback_file)
            if handback.status == "complete":
                # Route to Quality Engineer
                qe_delegate = create_qe_review_delegate(handback)
                send_to_qe(qe_delegate)
            elif handback.status == "blocked":
                # Route to Senior Engineer for diagnosis
                diagnosis_delegate = create_diagnosis_delegate(handback)
                send_to_senior_engineer(diagnosis_delegate)
        
        # 3. Check done/ for final decisions
        done = list_files("artifacts/queue/done/")
        for final_file in done:
            result = load_yaml(final_file)
            if result.decision == "PROCEED":
                merge(result.repo, result.commit)
            elif result.decision == "REWORK":
                new_delegate = create_rework_delegate(result)
                send_to_incoming(new_delegate)
            elif result.decision == "ESCALATE":
                escalate(result.task_id, result.escalation_reason)
        
        sleep(30)  # Poll every 30 seconds
```

---

## Red-Green TDD Integration

### DELEGATE Enforcement

When Orchestrator creates a DELEGATE for code changes:

```yaml
red_green_tdd_required: true
plan:
  1. [RED] Write failing test demonstrating the bug/requirement
  2. [GREEN] Implement minimal fix to pass the test
  3. [REFACTOR] Clean up code, improve error handling
  4. Run full test suite: "make verify"
  5. Verify success_criteria
```

### HANDBACK Validation

Engineer MUST include `red_green_evidence` showing each phase:

```yaml
red_green_tdd_applied: true
red_green_evidence:
  - "[RED] TestTokenExpiry_30sGracePeriod added, FAILS as expected"
  - "[GREEN] Modified line 92 to accept tokens within grace period, test PASSES"
  - "[REFACTOR] Extracted magic number 30 to const GRACE_PERIOD_SECS; improved error message"
  - "Full suite: 'make verify' PASS (47 tests, 89% coverage)"
```

**QE Verification:**
- If `red_green_tdd_applied: false` but should be `true` → **REJECT** (status: rejected)
- If evidence is missing → **REJECT** with feedback: "Provide Red-Green evidence"
- If evidence shows no REFACTOR phase → **ACCEPT** but note in feedback

### Quality Engineer Feedback

```yaml
qe_feedback:
  tier_1_verdict: PASS
  red_green_tdd_applied: true
  red_green_quality:
    red_phase_clear: true
    green_phase_minimal: true
    refactor_phase_present: true
    comment: "Clean Red-Green cycle; error handling improved in refactor"
  model_assessment: "haiku_suitable"
  confidence_for_similar_tasks: 0.94
```

---

## Rejection & Rework Loop

When QE rejects a HANDBACK:

1. QE stores HANDBACK in `done/{task_id}-rejected.yaml`
2. Orchestrator creates new DELEGATE:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-30-fix-token-timeout-rework-1
role: Engineer
model: claude-haiku-4-5
effort: high
scope: "Rework of task 2026-04-30-fix-token-timeout; address QE feedback below"
rejection_from_qe:
  - "Red-Green TDD evidence missing: no RED phase documented"
  - "Test coverage dropped from 89% to 87%"
  - "Error handling: panics on invalid token format"
context:
  - Previous HANDBACK: "queue/done/2026-04-30-fix-token-timeout-rejected.yaml"
  - QE detailed feedback: "See qe_feedback block in HANDBACK"
  - Files affected: lambda/api/main.go, lambda/api/main_test.go
plan:
  1. Read QE feedback in previous HANDBACK
  2. Address each rejection reason:
     a. Document the Red-Green cycle with evidence
     b. Add missing tests to restore coverage
     c. Add error handling for invalid token format
  3. Run "make verify" — all tests pass
  4. Re-submit
success_criteria:
  - QE feedback all addressed
  - "make verify" passes
  - Test coverage ≥87%
---
```

**Retry Limit:**
- After 3 rejections on same task → Escalate to Senior Engineer for diagnosis
- Store rejection count in task metadata

---

## Escalation Paths (Defined in AGENTS.md)

### Blocked Task (Agent Reports `status: blocked`)

**Example:** Engineer hits merge conflict or needs architectural decision.

```yaml
handoff_type: HANDBACK
status: blocked
blockers:
  - "Cannot implement token grace period without breaking API contract in {service-name} service"
  - "Requires decision: should we bump API version or add compatibility layer?"
```

**Orchestrator Routes To:** Lead Engineer or Principal Engineer (per AGENTS.md routing rules)

**New DELEGATE:**
```yaml
role: Senior Engineer  # or Lead Engineer, per AGENTS.md
scope: "Unblock token grace period task; diagnose architectural constraint and recommend approach"
context:
  - Previous HANDBACK (blocked): "queue/processing/{task_id}-HANDBACK.yaml"
  - Blocked reason: Token grace period breaks API contract with {service-name}
plan:
  1. Analyze API contract changes required
  2. Compare options: version bump vs. compatibility layer
  3. Recommend approach with rationale
  4. If simple fix: provide implementation plan for Engineer rework
```

---

## Fast-Track Criteria (Auto-Merge)

Work proceeds straight from `done/complete` to merge **only if**:

```yaml
---
handoff_type: DELEGATE
fast_track_eligible: true  # Orchestrator set based on scope
tier: 1  # Tier 1 = simple, low-risk changes
scope: "Fix typo in comment; low risk"
```

After QE verification, **if all true:**
- ✅ `red_green_tdd_applied: true` (or `red_green_tdd_required: false` for analysis)
- ✅ Tests: PASS, coverage maintained or improved
- ✅ No security findings
- ✅ Lint passes, no style violations
- ✅ Rejection count = 0
- ✅ Escalations = 0

**Then:** Orchestrator auto-merges to main; no manual review needed.

**Otherwise:** Requires human review before merge.

---

## Queue Monitoring & Metrics

### Orchestrator Status Report (Every 4 hours)

```yaml
---
report_type: ORCHESTRATOR_STATUS
timestamp: "2026-04-30T14:00:00Z"
queue_snapshot:
  incoming:
    count: 0
    oldest: null
  processing:
    count: 2
    oldest_task_id: "2026-04-30-fix-token-timeout"
    oldest_age_minutes: 45
  done:
    count: 5
    last_decision: "PROCEED"
metrics:
  total_tasks_completed: 127
  completion_rate: 0.94  # 127 complete / 135 total
  avg_duration_minutes: 18.4
  rejection_rate: 0.06  # 8 rejections / 127 completed
  escalation_rate: 0.04  # 5 escalations / 127 completed
  model_distribution:
    "claude-haiku-4-5": 0.58
    "claude-sonnet-4-6": 0.35
    "claude-opus-4-7": 0.07
  cost_efficiency: 0.87  # cost_actual / cost_predicted (target: >0.85)
bottlenecks:
  - "Processing queue building: 2 tasks > 40min (normal: <30min)"
  - "No current blockers"
recommendations:
  - "Monitor processing queue; may need parallel QE capacity"
---
```

---

## Integration with AGENTS.md

The DELEGATE protocol **references AGENTS.md** for routing rules:

```yaml
---
handoff_type: DELEGATE
# Orchestrator uses AGENTS.md routing logic to populate these:
role: Engineer
model: claude-haiku-4-5
# (See AGENTS.md "Routing Decision Tree" for how Orchestrator chose Engineer)
---
```

**Required AGENTS.md Sections:**
1. **Routing Decision Tree** — Used by Orchestrator when assigning roles
2. **Escalation Rules** — When to promote from Engineer → Senior Engineer, etc.
3. **Rejection & Rework Rules** — Retry limits, when to escalate blocked tasks
4. **Fast-Track Criteria** — Which task types auto-merge without review

---

## SKILLS.md Integration

Each agent role has a **SKILLS.md** defining its capabilities and workflows:

**Example: Engineer SKILLS.md**
```
# Engineer Skills

## Red-Green TDD
- MUST: Write failing test first (RED phase)
- MUST: Implement minimal fix (GREEN phase)
- SHOULD: Refactor and improve (REFACTOR phase)
- EVIDENCE: Document each phase in HANDBACK.red_green_evidence

## Error Handling
- MUST: Never panic on unexpected input
- SHOULD: Validate at boundaries (user input, external APIs)
- SHOULD: Provide actionable error messages

## Code Review Checklist
- [ ] Tests cover happy path and edge cases
- [ ] No new warnings in linter
- [ ] Error handling is defensive
- [ ] No hardcoded values (extract to constants)
- [ ] Comments explain WHY, not WHAT
```

Agent reads SKILLS.md when starting work, ensuring consistent quality.

---

## Archive & Historical Lookup

After task completes and leaves the active queue:

**Move to:** `artifacts/archive/YYYY-MM-DD/{task_id}/{DELEGATE,HANDBACK,QE_FEEDBACK}.yaml`

**Indexing:** `artifacts/archive/index.jsonl` (one JSON per line)
```json
{"task_id": "2026-04-30-fix-token-timeout", "date": "2026-04-30", "role": "Engineer", "status": "complete", "model": "claude-haiku-4-5"}
```

**Use for:**
- Pattern recognition (Model Engineer: which models suit which task types?)
- Historical analysis (cost trends, rejection rates by task type)
- Replay / re-process (if needed, load old DELEGATE and re-run with updated code)

---

## Future: Database Migration

This queue protocol is file-based for simplicity. Later phases can migrate to:

```sql
CREATE TABLE tasks (
  task_id VARCHAR PRIMARY KEY,
  status ENUM ('incoming', 'processing', 'done'),
  role VARCHAR,
  model VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  delegate_artifact JSONB,
  handback_artifact JSONB,
  qe_feedback JSONB,
  final_decision VARCHAR
);

CREATE TABLE feedback_loops (
  task_id VARCHAR,
  feedback_type VARCHAR ('model_recommendation', 'pattern', 'rejection_reason'),
  feedback_data JSONB,
  created_at TIMESTAMP
);
```

**API Endpoints (future):**
- `GET /tasks/{task_id}` — Fetch full task history
- `POST /tasks/{task_id}/handback` — Submit HANDBACK
- `GET /tasks?status=processing&role=Engineer` — List active tasks
- `GET /feedback/patterns?task_type=bug_fix` — Pattern analysis

---

## Summary: Files Stored

| Type | Path | When | Who |
|------|------|------|-----|
| DELEGATE | `delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator creates | Orchestrator |
| HANDBACK | `queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent completes | Agent |
| QE Feedback | `queue/done/{task_id}-qe-feedback.yaml` | QE verifies | Quality Engineer |
| Final Decision | `queue/done/{task_id}-{status}.yaml` | Orchestrator decides next step | Orchestrator |
| Archive | `archive/YYYY-MM-DD/{task_id}/*` | After task leaves queue | Archival |
| Feedback Loop | `feedback/{type}/{pattern}.jsonl` | During Model Engineer analysis | Model Engineer |

