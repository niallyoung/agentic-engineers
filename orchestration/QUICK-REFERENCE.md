# Quick Reference: Queue-Based Architecture

Visual guide to the refactored system. See [ARCHITECTURE-INTEGRATION.md](ARCHITECTURE-INTEGRATION.md) for complete examples.

---

## Architecture at a Glance

```
┌────────────────────────────────────────────────────────────────┐
│ User / External System                                         │
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
        ┌──────────────────────────────┐
        │ artifacts/queue/incoming/    │ ← New task arrives
        │ {task_id}-NEW.yaml           │
        └───────────────┬──────────────┘
                        │
     ┌──────────────────┴──────────────────┐
     │                                      │
     ▼                                      │
┌────────────────────────┐                 │
│  ORCHESTRATOR          │                 │
│  (Haiku, Low)          │                 │
│                        │                 │
│ 1. Read AGENTS.md      │                 │ Runs every
│    routing rules       │                 │ 30-60 seconds
│ 2. Create DELEGATE     │                 │
│ 3. Send to agent       │                 │
└────────────────────────┘                 │
     │                                      │
     │ Creates DELEGATE                    │
     │ Stores in artifacts/delegates/     │
     │ Sends to agent role                │
     │                                      │
     ▼                                      │
┌────────────────────────────────────────┐ │
│ artifacts/queue/processing/            │ │
│ {task_id}-HANDBACK-{role}.yaml         │ │
│                                        │ │
│ Agent receives DELEGATE:               │ │
│ • Reads SKILLS.md for guidance        │ │
│ • Executes work per plan              │ │
│ • For code: applies Red-Green TDD    │ │
│ • Returns HANDBACK with evidence     │ │
│ • Documents red_green_evidence       │ │
└────────────────────────────────────────┘ │
     │                                      │
     ▼                                      │
┌────────────────────────┐                 │
│  QUALITY ENGINEER      │                 │
│  (Sonnet, Medium)      │                 │
│                        │                 │
│ 1. Run Tier 1/2 checks │                 │
│ 2. Verify Red-Green    │                 │ Triggered when
│    TDD evidence        │                 │ HANDBACK arrives
│ 3. Add qe_feedback     │                 │
└────────────────────────┘                 │
     │                                      │
     ├─ PASS? ──────────────┐              │
     │                      ▼              │
     │            ┌──────────────────────┐ │
     │            │ artifacts/queue/    │ │
     │            │ done/               │ │
     │            │ {task_id}-complete  │ │
     │            └──────────────────────┘ │
     │                      │              │
     │                      ▼              │
     │            ┌──────────────────────┐ │
     │            │ ORCHESTRATOR         │ │
     │            │ Fast-Track Check?    │ │
     │            │ • All gates PASS     │ │
     │            │ • No escalations     │ │
     │            │ • Red-Green evidence │ │
     │            │ • Tier 1 scope       │ │
     │            └──────────────────────┘ │
     │                      │              │
     │         ┌────────────┬──────────────┤
     │         ▼            ▼              │
     │    YES:         NO:                 │
     │   Auto-        Notify human        │
     │   Merge        for review          │
     │                                     │
     └─ FAIL (rejected)? ──────────────────┘
              │
              ▼
        ┌──────────────┐
        │ Create NEW   │
        │ DELEGATE     │
        │ with         │
        │ feedback     │
        │              │
        │ Return to    │
        │ incoming/    │
        │ for rework   │
        └──────────────┘
             │
             └─→ (Retry up to 3 times, then escalate)
```

---

## Document Map

| Document | Purpose | Owner | Audience |
|----------|---------|-------|----------|
| **AGENTS.md** | WHO + ROUTING | Architect | Orchestrator |
| **SKILLS.md** | WHAT + HOW | Role leads | Agents |
| **QUEUE-PROTOCOL.md** | WORKFLOW + AUTOMATION | Architect | Orchestrator, QE |
| **HANDOFF.md** | FORMAT + ENFORCEMENT | Architect | All agents |
| **ARCHITECTURE-INTEGRATION.md** | HOW IT FITS | Architect | All |

---

## Key Enforcement Points

### Red-Green TDD (MANDATORY for code changes)

```
DELEGATE specifies:
  red_green_tdd_required: true
  plan:
    1. [RED] Write failing test
    2. [GREEN] Implement minimal fix
    3. [REFACTOR] Improve code
    4. [VERIFY] Run full suite

Agent returns:
  red_green_tdd_applied: true
  red_green_evidence:
    - "[RED] Test added, FAILS"
    - "[GREEN] Fix applied, PASSES"
    - "[REFACTOR] Constant extracted, error message improved"
    - "[VERIFY] All tests pass, coverage maintained"

Quality Engineer verifies:
  ✓ RED phase documented?
  ✓ GREEN phase documented?
  ✓ REFACTOR phase present?
  ✓ Tests pass?
  ✗ Missing any? → REJECT
```

### Rejection Loop

```
First rejection: → Return to agent for rework
Second rejection: → Return to agent for rework
Third rejection: → Escalate to Senior Engineer for diagnosis

After rework:
  Agent resubmits with complete evidence
  QE re-verifies
  If PASS: Task proceeds
  If FAIL: Escalate to Senior Engineer
```

### Escalation Paths

```
STATUS: blocked → Lead Engineer or Senior Engineer
REASON: "Cannot implement without breaking API contract"

STATUS: rejected (3x) → Senior Engineer
REASON: "Agent unable to complete; needs diagnosis"

ROLE: Engineer (stuck) → Senior Engineer
ROLE: Senior Engineer (stuck) → Lead Engineer
ROLE: Any role (security Q) → Security Engineer
```

---

## Queue State Diagram

```
                    incoming/
                    (New task)
                        ↓
                  Orchestrator reads
                  AGENTS.md routes
                        ↓
                  Create DELEGATE
                  Store in delegates/
                        ↓
            ┌───────────┴────────────┐
            ▼                        ▼
        Send to            processing/
        agent              (Agent working)
                                ↓
                        Agent returns HANDBACK
                                ↓
                        Orchestrator polls
                        Routes to QE
                                ↓
        ┌───────────────────────┬───────────────────────┐
        ▼                       ▼                       ▼
    PASS ✓                   FAIL ✗              BLOCKED (status)
        │                       │                       │
        ├─→ done/           Rework                Escalate
        │   complete        DELEGATE              to Senior
        │                   sends to              Engineer
        ├─→ FAST-TRACK?      incoming/
        │                                         
        ├─ YES: Auto-merge
        │
        └─ NO: Notify human for review
```

---

## Task Status Values

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `complete` | All success_criteria met; ready for QE | Route to Quality Engineer |
| `partial` | Some criteria met; rest deferred | QE decides: accept or rework |
| `blocked` | Cannot proceed; needs help | Escalate to Senior Engineer |
| `rejected` | QE rejected (quality issue) | Create rework DELEGATE |

---

## Tier Checklist (What QE Verifies)

### Tier 1 (ALL code)
- [ ] Tests pass
- [ ] Lint clean
- [ ] Coverage maintained or improved
- [ ] No panics or hardcoded values
- [ ] Red-Green TDD evidence (if code change)

### Tier 2 (Senior+ code)
- [ ] Tier 1 + above
- [ ] Coverage ≥85%
- [ ] Plan completeness (all steps executed)
- [ ] Error handling defensive

### Tier 3 (Principal/Security code)
- [ ] Tier 1 & 2 + above
- [ ] Architecture adherence
- [ ] IAM/security correctness
- [ ] No breaking changes without migration

---

## Model Engineer Feedback Cycle

```
After 10-100 tasks complete:

Model Engineer analyzes:
  • Token usage per task type
  • QE verdict (model suitable? confidence?)
  • Rejection patterns (which models fail most?)
  • Efficiency (cost per quality point)

Generates recommendations:
  Rank 1 (highest confidence): Use this model for next task
  Rank 2 (exploratory): Consider A/B test
  Rank 3 (fallback): Use if rank 1 unavailable

Stored in:
  artifacts/feedback/model-recommendations.jsonl

Orchestrator applies:
  For next matching task, use Rank 1 model
  (instead of guessing or using default)

Result:
  Routing improves, cost decreases, quality increases
  System self-optimizes over time
```

---

## File Naming Conventions

```
incoming/:
  {task_id}-NEW.yaml
  Example: 2026-04-30-fix-token-timeout-NEW.yaml

processing/:
  {task_id}-HANDBACK-{role}.yaml
  Example: 2026-04-30-fix-token-timeout-HANDBACK-Engineer.yaml

done/:
  {task_id}-{status}.yaml
  Example: 2026-04-30-fix-token-timeout-complete.yaml
  Example: 2026-04-30-fix-token-timeout-rejected.yaml
  Example: 2026-04-30-fix-token-timeout-escalated.yaml

delegates/:
  YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml
  Example: 2026-04-30/DELEGATE-2026-04-30-fix-token-timeout-Engineer.yaml

archive/:
  YYYY-MM-DD/{task_id}/
    ├── DELEGATE.yaml
    ├── HANDBACK.yaml
    └── QE_FEEDBACK.yaml
```

---

## Orchestrator Polling Loop (Pseudocode)

```python
while True:
    # Every 30-60 seconds
    
    # 1. Check for new work
    for task in list_files("artifacts/queue/incoming/"):
        delegate = create_delegate_from_task(task)
        store_delegate("artifacts/delegates/", delegate)
        route_to_agent(delegate.role, delegate)
        move(task, "artifacts/queue/processing/")
    
    # 2. Check for work completion
    for handback in list_files("artifacts/queue/processing/"):
        if handback.status == "complete":
            route_to_quality_engineer(handback)
        elif handback.status == "blocked":
            escalate_to_senior_engineer(handback)
    
    # 3. Check for final decisions
    for result in list_files("artifacts/queue/done/"):
        if result.decision == "PROCEED":
            if is_fast_track(result):
                merge_to_main(result.repo, result.commit)
            else:
                notify_human(result)
        elif result.decision == "REWORK":
            rework_delegate = create_rework_delegate(result)
            move_to_incoming(rework_delegate)
        elif result.decision == "ESCALATE":
            escalate_to_lead_engineer(result)
    
    sleep(30)  # Poll every 30 seconds
```

---

## Integration Checklist (Before Going Live)

- [ ] AGENTS.md reads and understood by team
- [ ] SKILLS.md read by each agent role (know your section)
- [ ] QUEUE-PROTOCOL.md implemented in code (Orchestrator loop)
- [ ] HANDOFF.md format used for all DELEGATE/HANDBACK blocks
- [ ] Red-Green TDD verified on first 5 tasks (check evidence)
- [ ] Rejection loop tested (task rejected → rework → resubmit)
- [ ] Escalation tested (blocked task → escalate → resolve)
- [ ] Fast-track tested (task auto-merges without human review)
- [ ] Model Engineer recommendations generated after 10+ tasks
- [ ] Archive system working (old tasks move to archive/)

---

## Quick Answers

**Q: What if I get blocked?**  
A: Mark status=blocked in HANDBACK; Orchestrator escalates to Senior Engineer.

**Q: What if QE rejects my task?**  
A: Orchestrator creates rework DELEGATE with specific feedback. Resubmit. (Max 3 rejections before escalate.)

**Q: Do I need to write a failing test first?**  
A: YES. Red-Green TDD is mandatory for code changes. Evidence must be in HANDBACK.

**Q: Can a task auto-merge without review?**  
A: YES, if it's FAST-TRACK (low-risk, all gates pass, Red-Green evidence clear). Otherwise human review required.

**Q: How do I know what skill to use?**  
A: Read SKILLS.md section for your role. It has step-by-step workflows.

**Q: How long before the system improves?**  
A: Model Engineer recommendations kickin after ~10-100 completed tasks. Cost/efficiency improves ~3% per task after that.

---

## See Also

- [AGENTS.md](AGENTS.md) — Role definitions and routing rules
- [SKILLS.md](SKILLS.md) — Role-specific workflows and quality standards
- [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md) — Complete queue system specification
- [HANDOFF.md](HANDOFF.md) — DELEGATE/HANDBACK format and rules
- [ARCHITECTURE-INTEGRATION.md](ARCHITECTURE-INTEGRATION.md) — How it all fits together with examples

