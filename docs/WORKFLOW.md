---
name: SDLC Workflow with Enforcement Points
description: Complete lifecycle from user request to production, with enforcement gates at each stage
version: 1.0
updated: 2026-05-16
status: Production Ready
---

# SDLC Workflow with Enforcement Points

**Last Updated:** 2026-05-16  
**Scope:** Complete SDLC lifecycle from user request through production deployment  
**Status:** Production Ready — All enforcement points implemented and tested

---

## Executive Summary

The agentic-engineers SDLC enforces quality and compliance at **7 critical gates**:

1. **User Request Gate** — Scope validation
2. **Orchestrator Gate** — Routing decision
3. **DELEGATE Gate** — Task structure validation
4. **Agent Execution Gate** — Quality baseline
5. **HANDBACK Gate** — Result validation
6. **Pre-Commit Gate** — SPEC compliance, secrets, format
7. **Pre-Push Gate** — Final quality verification

Each gate has clear decision rules, what happens on failure, and escalation paths.

---

## Complete SDLC Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST (GATE 1)                               │
│                                                                             │
│  Input: Task description, scope, context                                   │
│  Validation: Is scope clear? Is it bounded? Is success measurable?         │
│  Decision: ACCEPT → Orchestrator | REJECT → Ask for clarification         │
│  Output: Task ID (YYYY-MM-DD-kebab-case), queue entry                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR GATE (GATE 2)                             │
│                                                                             │
│  Input: Task from queue                                                    │
│  Process:                                                                   │
│    1. Apply AGENTS.md routing decision tree                                │
│    2. Select appropriate agent (Engineer, Senior Engineer, etc.)           │
│    3. Determine effort level (low, medium, high, max)                      │
│    4. Assign model (Haiku, Sonnet, Opus)                                   │
│  Decision: Route to {Agent} | Escalate if unclear                          │
│  Output: DELEGATE block with routing decision                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DELEGATE GATE (GATE 3)                                │
│                                                                             │
│  Input: DELEGATE block from Orchestrator                                   │
│  Validation:                                                                │
│    ✓ All required fields present (task_id, role, scope, plan, etc.)       │
│    ✓ YAML syntax valid                                                     │
│    ✓ Task ID format correct (YYYY-MM-DD-kebab-case)                       │
│    ✓ Role is valid (Engineer, Senior Engineer, etc.)                       │
│    ✓ Effort level is valid (low, medium, high, max)                        │
│    ✓ Plan is concrete and numbered (required for Engineer)                 │
│    ✓ Success criteria are testable                                         │
│    ✓ No secrets in DELEGATE block                                          │
│  Decision: ACCEPT → Agent Work | REJECT → Orchestrator fixes              │
│  Output: DELEGATE stored in artifacts/delegates/YYYY-MM-DD/               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT EXECUTION (GATE 4)                               │
│                                                                             │
│  Input: DELEGATE block                                                     │
│  Execution:                                                                 │
│    1. Read DELEGATE and understand scope                                   │
│    2. Execute plan step-by-step                                            │
│    3. Run tests/verification                                               │
│    4. Measure quality metrics                                              │
│    5. Capture token usage                                                  │
│  Quality Baseline:                                                          │
│    ✓ All tests passing                                                     │
│    ✓ Code coverage maintained (≥85% for critical code)                     │
│    ✓ No regressions                                                        │
│    ✓ Confidence score ≥80%                                                 │
│  Decision: COMPLETE → HANDBACK | BLOCKED → Escalate | FAILED → Rework    │
│  Output: HANDBACK block with results and metrics                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HANDBACK GATE (GATE 5)                               │
│                                                                             │
│  Input: HANDBACK block from Agent                                          │
│  Validation:                                                                │
│    ✓ All required fields present (task_id, status, deliverables, etc.)    │
│    ✓ YAML syntax valid                                                     │
│    ✓ Status is valid (complete, failed, partial, blocked)                  │
│    ✓ Deliverables match DELEGATE scope                                     │
│    ✓ Tests documented with pass/fail counts                                │
│    ✓ Quality score is honest (0-100)                                       │
│    ✓ Token usage documented                                                │
│    ✓ No scope creep (work stayed in DELEGATE bounds)                       │
│  Quality Scoring:                                                           │
│    Format (40%): YAML valid, required fields present                       │
│    Content (35%): Deliverables match scope, tests passing                  │
│    Quality (25%): Code quality, coverage, confidence                       │
│    Composite: 0-100 score                                                  │
│  Decision:                                                                  │
│    90-100: MERGE (immediate)                                               │
│    80-89:  MERGE (with notes)                                              │
│    70-79:  LEAD REVIEW (manual verification)                               │
│    60-69:  REWORK (max 2 retries, then escalate)                           │
│    <60:   ESCALATE (to Principal Engineer)                                 │
│  Output: HANDBACK stored in artifacts/queue/processing/                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PRE-COMMIT GATE (GATE 6)                                  │
│                                                                             │
│  Trigger: git commit                                                        │
│  Validation:                                                                │
│    ✓ SPEC.md compliance (no external scripts, cron files, etc.)            │
│    ✓ Secret detection (API keys, passwords, tokens)                        │
│    ✓ YAML/JSON syntax valid                                                │
│    ✓ File format (line endings, trailing whitespace)                       │
│    ✓ Code style (flake8, shellcheck if available)                          │
│    ✓ No bypass markers in code                                             │
│    ✓ DELEGATE/HANDBACK blocks have required fields (if present)            │
│  Decision:                                                                  │
│    ✓ All checks pass → Commit created                                      │
│    ✗ Errors found → BLOCK commit, show errors                              │
│    ⚠ Warnings only → Proceed (non-blocking)                                │
│  Bypass: SKIP_HOOKS=1 git commit (requires documented reason)              │
│  Output: Commit created and ready to push                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRE-PUSH GATE (GATE 7)                                   │
│                                                                             │
│  Trigger: git push                                                          │
│  Validation:                                                                │
│    ✓ Agent YAML frontmatter valid (src/agents/*.md)                        │
│    ✓ Workflow files valid (.github/workflows/*.yml)                        │
│    ✓ Documentation consistency (SPEC.md, AGENTS.md, README.md)             │
│    ✓ DELEGATE/HANDBACK protocol compliance (artifacts/)                    │
│    ✓ Test suite passing (pytest if available)                              │
│    ✓ SPEC compliance (no external scripts, cron files)                     │
│  Decision:                                                                  │
│    ✓ All checks pass → Push proceeds                                       │
│    ✗ Errors found → BLOCK push, show errors                                │
│    ⚠ Warnings only → Proceed (non-blocking)                                │
│  Bypass: SKIP_HOOKS=1 git push (requires documented reason)                │
│  Output: Code pushed to remote, ready for merge                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MERGE TO MAIN (FINAL)                                  │
│                                                                             │
│  Requirement: Pull request approved by Lead Engineer or above              │
│  Quality Engineer review: Complete (quality_score documented)              │
│  All gates passed: Yes (pre-commit, pre-push)                              │
│  Tests: All passing                                                        │
│  CI/CD: Green                                                              │
│  Decision: MERGE → Code in production                                      │
│  Output: Metrics recorded, feedback to Model Engineer                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Gate Details & Decision Trees

### Gate 1: User Request

**Input:** Task description from user

**Validation Checklist:**
- [ ] Scope is clear and bounded (not "improve everything")
- [ ] Success criteria are measurable (not "make it better")
- [ ] Context is provided (relevant files, errors, background)
- [ ] Effort estimate is reasonable (not "unknown")
- [ ] No external dependencies blocking work

**Decision Tree:**

```
Is scope clear and bounded?
├─ YES → Is success measurable?
│        ├─ YES → Is context sufficient?
│        │        ├─ YES → ACCEPT (create queue entry)
│        │        └─ NO → ASK FOR CONTEXT
│        └─ NO → ASK FOR MEASURABLE CRITERIA
└─ NO → ASK FOR SCOPE CLARIFICATION
```

**What Happens on Failure:**
- Ask user to clarify scope
- Request measurable success criteria
- Provide context template if needed
- Do NOT create queue entry until scope is clear

**Output:**
- Task ID: `YYYY-MM-DD-kebab-case`
- Queue entry in `artifacts/queue/incoming/{task_id}.yaml`

---

### Gate 2: Orchestrator Routing

**Input:** Task from queue

**Routing Decision Tree (from AGENTS.md):**

```
Is task security-scoped?
├─ YES → Route to Security Engineer (Opus 4.7, max effort)
└─ NO → Is task cross-service architecture (affects >2 repos)?
        ├─ YES → Route to Principal Engineer (Opus 4.6, high effort)
        └─ NO → Is task complex coding WITHOUT pre-written plan?
                ├─ YES → Route to Senior Engineer (Sonnet, high effort)
                │        [Senior Engineer writes plan first]
                └─ NO → Is task code review or quality verification?
                        ├─ YES → Route to Lead Engineer or Quality Engineer (Sonnet)
                        └─ NO → Is task well-planned, low-medium complexity?
                                ├─ YES → Route to Engineer (Haiku, high effort)
                                └─ NO → Escalate to human (unclear scope)
```

**What Happens on Failure:**
- If routing is unclear → Escalate to human for clarification
- If task is blocked → Document blocker and notify requester
- If effort estimate is wrong → Adjust and re-route

**Output:**
- DELEGATE block with:
  - `role`: {Engineer|Senior Engineer|Lead Engineer|...}
  - `model`: {claude-haiku-4-5|claude-sonnet-4-6|claude-opus-4-6|...}
  - `effort`: {low|medium|high|max}
  - `scope`: Clear description of work
  - `context`: Background information
  - `plan`: Numbered steps (required for Engineer)
  - `success_criteria`: Testable acceptance criteria
  - `estimated_tokens`: Budget estimate

---

### Gate 3: DELEGATE Validation

**Input:** DELEGATE block from Orchestrator

**Validation Checklist:**

```yaml
handoff_type: DELEGATE              # ✓ Required, must be "DELEGATE"
task_id: YYYY-MM-DD-kebab-case      # ✓ Required, correct format
role: Engineer                       # ✓ Required, valid role
model: claude-haiku-4-5              # ✓ Required, valid model
effort: high                         # ✓ Required, valid level
scope: |                             # ✓ Required, ≥15 words, clear
  Clear description of work
context:                             # ✓ Required, relevant background
  - Key files: path/to/files
  - Related issues: #123
plan:                                # ✓ Required for Engineer, numbered
  1. First step
  2. Second step
success_criteria:                    # ✓ Required, testable
  - All tests passing
  - Coverage ≥85%
estimated_tokens: 1500               # ✓ Required, reasonable estimate
```

**Validation Rules:**

| Field | Rule | Error |
|-------|------|-------|
| `handoff_type` | Must be "DELEGATE" | `Invalid handoff_type` |
| `task_id` | Format: YYYY-MM-DD-kebab-case | `Invalid task_id format` |
| `role` | Must be valid role | `Invalid role` |
| `model` | Must be valid model | `Invalid model` |
| `effort` | Must be low/medium/high/max | `Invalid effort level` |
| `scope` | ≥15 words, clear | `Scope too vague` |
| `context` | Relevant background | `Insufficient context` |
| `plan` | Numbered steps (for Engineer) | `Plan missing or not numbered` |
| `success_criteria` | Testable, measurable | `Criteria not testable` |
| `estimated_tokens` | Reasonable for effort | `Token estimate unrealistic` |
| YAML syntax | Valid YAML | `Invalid YAML syntax` |
| No secrets | No API keys, passwords | `Secrets detected` |

**What Happens on Failure:**
- If validation fails → Reject DELEGATE, return to Orchestrator
- Orchestrator fixes issues and re-submits
- If issues persist → Escalate to Senior Engineer

**Output:**
- DELEGATE stored in `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`
- Task moved to `artifacts/queue/processing/`

---

### Gate 4: Agent Execution

**Input:** DELEGATE block

**Execution Process:**

```
1. READ & VALIDATE DELEGATE
   ├─ Verify all required fields present
   ├─ Verify scope is clear
   ├─ Verify plan is concrete (for Engineer)
   └─ If issues found → Report status: blocked

2. EXECUTE PLAN (step-by-step)
   ├─ For each step:
   │  ├─ Perform action
   │  ├─ Capture result
   │  ├─ Check: Does this align with success criteria?
   │  └─ If blocked: Document blocker, continue
   └─ All steps complete

3. RUN TESTS/VERIFICATION
   ├─ Execute success criteria checks
   ├─ Run test suite (make verify or pytest)
   ├─ Measure code coverage
   └─ Confirm deliverables complete

4. MEASURE QUALITY
   ├─ Tests passing: Y/N
   ├─ Coverage: X%
   ├─ Confidence: 0.0-1.0
   ├─ Any shortcuts taken: Y/N
   └─ Edge cases missed: None/Some/Many

5. CAPTURE METRICS
   ├─ Tokens used: {actual}
   ├─ Tokens estimated: {from DELEGATE}
   ├─ Duration: {minutes}
   ├─ Quality score: {0-100}
   └─ Confidence: {0.0-1.0}
```

**Quality Baseline:**
- ✅ All tests passing
- ✅ Code coverage maintained (≥85% for critical code)
- ✅ No regressions
- ✅ Confidence ≥80%

**What Happens on Failure:**
- If tests fail → Fix and re-run
- If coverage drops → Add tests
- If blocked → Report `status: blocked` in HANDBACK
- If scope creep → Document in HANDBACK notes

**Output:**
- HANDBACK block with:
  - `task_id`: Same as DELEGATE
  - `status`: complete|failed|partial|blocked
  - `deliverables`: List of files changed
  - `tests`: Test results with pass/fail counts
  - `tokens_used`: Actual token count
  - `tokens_estimated`: From DELEGATE
  - `quality_score`: 0-100
  - `confidence`: 0.0-1.0
  - `notes`: What went well, what was hard

---

### Gate 5: HANDBACK Validation

**Input:** HANDBACK block from Agent

**Validation Checklist:**

```yaml
handoff_type: HANDBACK               # ✓ Required, must be "HANDBACK"
task_id: YYYY-MM-DD-kebab-case       # ✓ Required, matches DELEGATE
status: complete                     # ✓ Required, valid status
deliverables:                        # ✓ Required, list of changes
  - Modified: src/file.py
  - Added: tests/test_file.py
tests:                               # ✓ Required, test results
  - pytest: PASS (47 tests)
  - coverage: 87%
quality_score: 95                    # ✓ Required, 0-100
tokens_used: 1200                    # ✓ Required, actual count
tokens_estimated: 1500               # ✓ Required, from DELEGATE
duration_minutes: 18                 # ✓ Required, wall clock time
confidence: 0.95                     # ✓ Required, 0.0-1.0
notes: |                             # ✓ Required, summary
  Implementation complete, all tests passing
```

**Quality Scoring Formula:**
- **Format (40%):** YAML valid, required fields present
- **Content (35%):** Deliverables match scope, tests passing
- **Quality (25%):** Code quality, coverage, confidence
- **Composite:** (Format × 0.4) + (Content × 0.35) + (Quality × 0.25)

**Routing by Score:**

| Score | Decision | Next Step |
|-------|----------|-----------|
| 90-100 | MERGE | Move to done/, ready for production |
| 80-89 | MERGE | Move to done/, with notes |
| 70-79 | LEAD REVIEW | Manual verification by Lead Engineer |
| 60-69 | REWORK | Create new DELEGATE with feedback (max 2 retries) |
| <60 | ESCALATE | Principal Engineer reviews, decides next step |

**What Happens on Failure:**
- If validation fails → Reject HANDBACK, return to Agent
- Agent fixes issues and re-submits
- If rework needed → Create new DELEGATE with feedback
- If escalation needed → Route to Principal Engineer

**Output:**
- HANDBACK stored in `artifacts/queue/processing/{task_id}-HANDBACK.yaml`
- Metrics recorded for Model Engineer
- Task moved to `artifacts/queue/done/` after QE review

---

### Gate 6: Pre-Commit (SPEC & Quality)

**Trigger:** `git commit`

**Validation Checklist:**

```
SPEC.md Compliance
├─ No .py/.sh in orchestration/scripts/
├─ No .cron in orchestration/config/
├─ No subprocess/os.system/exec in agent code
└─ No external scripts (except renderer/)

Secret Detection
├─ No API keys (api_key, secret_key, private_key)
├─ No AWS keys (AKIA[0-9A-Z]{16})
├─ No GitHub tokens (ghp_*)
├─ No private key headers (BEGIN RSA PRIVATE KEY)
├─ No hardcoded database credentials
└─ No hardcoded HTTP authentication

YAML/JSON Validity
├─ All .yaml/.yml files parse as valid YAML
├─ All .json/.jsonc files parse as valid JSON
└─ JSONC comments properly stripped

File Format
├─ No DOS line endings (CRLF)
└─ No trailing whitespace

Code Style (warnings only)
├─ flake8 checks (if installed)
└─ shellcheck checks (if installed)

Security Integration
├─ No hardcoded database URLs
├─ No hardcoded API endpoints with auth
├─ No dangerous shell patterns (eval, set +e)
└─ No bypass markers in code

DELEGATE/HANDBACK Validation (if present)
├─ YAML syntax valid
├─ Required fields present
├─ Task ID format correct
└─ Status values valid
```

**Decision:**
- ✓ All checks pass → Commit created
- ✗ Errors found → BLOCK commit
- ⚠ Warnings only → Proceed (non-blocking)

**Bypass:**
```bash
SKIP_HOOKS=1 git commit -m "emergency: reason"
BYPASS_HOOK_VALIDATION=true git commit -m "message"
```

**Output:**
- Commit created and ready to push

---

### Gate 7: Pre-Push (Final Quality Gate)

**Trigger:** `git push`

**Validation Checklist:**

```
Protected Branch Detection
└─ Warn if pushing to main/master

Agent YAML Frontmatter (src/agents/*.md)
├─ Valid YAML syntax
├─ Required fields: name, role, model, effort
└─ All agent definitions valid

Workflow Files (.github/workflows/*.yml)
├─ Valid YAML syntax
├─ Required fields: name, on (trigger)
└─ All workflows valid

Documentation Consistency
├─ docs/SPEC.md exists with version field
├─ docs/AGENTS.md exists with top-level heading
└─ README.md exists

DELEGATE/HANDBACK Protocol (artifacts/)
├─ All DELEGATE files valid YAML
├─ All DELEGATE files have required fields
├─ All HANDBACK files valid YAML
├─ All HANDBACK files have required fields
└─ No protocol violations

Test Suite (warnings only)
├─ pytest tests/ passes (if pytest available)
└─ All tests passing

SPEC Compliance
├─ No external scripts in orchestration/scripts/
├─ No cron files in orchestration/config/
└─ Makefile doesn't invoke external scripts
```

**Decision:**
- ✓ All checks pass → Push proceeds
- ✗ Errors found → BLOCK push
- ⚠ Warnings only → Proceed (non-blocking)

**Bypass:**
```bash
SKIP_HOOKS=1 git push
```

**Output:**
- Code pushed to remote, ready for merge

---

## Role Responsibilities at Each Stage

### User

**Gate 1: User Request**
- [ ] Provide clear, bounded scope
- [ ] Define measurable success criteria
- [ ] Provide relevant context (files, errors, background)
- [ ] Estimate effort level (rough)

### Orchestrator

**Gate 2: Orchestrator Routing**
- [ ] Apply AGENTS.md decision tree
- [ ] Select appropriate agent
- [ ] Determine effort level
- [ ] Create DELEGATE block with all required fields
- [ ] Store DELEGATE in artifacts/delegates/

**Gate 5: HANDBACK Validation**
- [ ] Score HANDBACK using formula
- [ ] Route based on score (merge/review/rework/escalate)
- [ ] Move to done/ or create rework DELEGATE
- [ ] Record metrics for Model Engineer

### Agent (Engineer, Senior Engineer, etc.)

**Gate 4: Agent Execution**
- [ ] Read and validate DELEGATE
- [ ] Execute plan step-by-step
- [ ] Run tests and verification
- [ ] Measure quality metrics
- [ ] Create HANDBACK with honest quality score
- [ ] Report blockers if encountered

### Quality Engineer

**Gate 5: HANDBACK Validation**
- [ ] Validate HANDBACK structure
- [ ] Verify deliverables match scope
- [ ] Check test results
- [ ] Assess code quality
- [ ] Score using formula
- [ ] Provide model assessment feedback

### Lead Engineer

**Gate 5: HANDBACK Validation (70-79 scores)**
- [ ] Manual code review
- [ ] Verify quality baseline met
- [ ] Approve/reject/conditional approve
- [ ] Document decision

### Developer

**Gate 6: Pre-Commit**
- [ ] Ensure SPEC compliance
- [ ] No secrets in code
- [ ] Valid YAML/JSON
- [ ] Descriptive commit message

**Gate 7: Pre-Push**
- [ ] All tests passing
- [ ] Documentation updated
- [ ] DELEGATE/HANDBACK valid
- [ ] Ready for merge

---

## Metrics Collected at Each Stage

### Gate 1: User Request
- `request_id`: Task ID
- `request_timestamp`: When submitted
- `scope_clarity`: Clear/Unclear
- `success_criteria_measurable`: Yes/No

### Gate 2: Orchestrator Routing
- `routing_decision`: Which agent selected
- `effort_level`: low/medium/high/max
- `model_assigned`: Which model
- `estimated_tokens`: Budget estimate

### Gate 4: Agent Execution
- `tokens_used`: Actual token count
- `duration_minutes`: Wall clock time
- `tests_passed`: Count
- `tests_failed`: Count
- `code_coverage`: Percentage
- `quality_score`: 0-100
- `confidence`: 0.0-1.0

### Gate 5: HANDBACK Validation
- `quality_score_composite`: 0-100
- `routing_decision`: merge/review/rework/escalate
- `lead_review_required`: Yes/No
- `rework_count`: 0/1/2/escalate

### Gate 6: Pre-Commit
- `commit_timestamp`: When committed
- `files_changed`: Count
- `spec_violations`: Count
- `secrets_detected`: Count
- `yaml_errors`: Count

### Gate 7: Pre-Push
- `push_timestamp`: When pushed
- `tests_passing`: Yes/No
- `documentation_valid`: Yes/No
- `protocol_compliant`: Yes/No

---

## Escalation Paths

### From Gate 1 (User Request)
- **Unclear scope** → Ask user for clarification
- **Unmeasurable criteria** → Request measurable criteria
- **Insufficient context** → Provide template, ask for details

### From Gate 2 (Orchestrator Routing)
- **Unclear routing** → Escalate to human
- **Complex task** → Route to Senior Engineer first (for planning)
- **Security task** → Route to Security Engineer

### From Gate 3 (DELEGATE Validation)
- **Invalid DELEGATE** → Return to Orchestrator, fix and resubmit
- **Persistent issues** → Escalate to Senior Engineer

### From Gate 4 (Agent Execution)
- **Blocked task** → Report `status: blocked` in HANDBACK
- **Blocked task** → Orchestrator escalates to Senior Engineer
- **Failed task** → Orchestrator creates rework DELEGATE

### From Gate 5 (HANDBACK Validation)
- **Score 70-79** → Lead Engineer manual review
- **Score 60-69** → Create rework DELEGATE (max 2 retries)
- **Score <60** → Escalate to Principal Engineer
- **Persistent failures** → Escalate to Principal Engineer

### From Gate 6 (Pre-Commit)
- **SPEC violation** → Fix and re-commit
- **Secrets detected** → Remove and re-commit
- **Emergency** → Use bypass with documentation

### From Gate 7 (Pre-Push)
- **Tests failing** → Fix tests and re-push
- **Documentation missing** → Add documentation and re-push
- **Protocol violation** → Fix DELEGATE/HANDBACK and re-push
- **Emergency** → Use bypass with documentation

---

## Decision Trees by Gate

### Gate 1: Should We Accept This Request?

```
START
  │
  ├─ Is scope clear and bounded?
  │  ├─ NO → ASK: "Please clarify scope"
  │  └─ YES ↓
  │
  ├─ Are success criteria measurable?
  │  ├─ NO → ASK: "Define measurable success criteria"
  │  └─ YES ↓
  │
  ├─ Is context sufficient?
  │  ├─ NO → ASK: "Provide relevant context"
  │  └─ YES ↓
  │
  └─ ACCEPT: Create queue entry
     └─ Output: Task ID, queue entry
```

### Gate 2: Which Agent Should Handle This?

```
START
  │
  ├─ Is task security-scoped?
  │  ├─ YES → Route to Security Engineer (Opus 4.7, max)
  │  └─ NO ↓
  │
  ├─ Does task affect >2 repos (cross-service)?
  │  ├─ YES → Route to Principal Engineer (Opus 4.6, high)
  │  └─ NO ↓
  │
  ├─ Is task complex coding WITHOUT pre-written plan?
  │  ├─ YES → Route to Senior Engineer (Sonnet, high)
  │  │        [Senior Engineer writes plan first]
  │  └─ NO ↓
  │
  ├─ Is task code review or quality verification?
  │  ├─ YES → Route to Lead Engineer or QE (Sonnet)
  │  └─ NO ↓
  │
  ├─ Is task well-planned, low-medium complexity?
  │  ├─ YES → Route to Engineer (Haiku, high)
  │  └─ NO ↓
  │
  └─ Escalate to human (unclear scope)
```

### Gate 5: What Do We Do With This HANDBACK?

```
START
  │
  ├─ Is HANDBACK valid (YAML, required fields)?
  │  ├─ NO → REJECT: Return to agent, fix and resubmit
  │  └─ YES ↓
  │
  ├─ Calculate quality score (format + content + quality)
  │  │
  │  ├─ Score 90-100?
  │  │  ├─ YES → MERGE: Move to done/, ready for production
  │  │  └─ NO ↓
  │  │
  │  ├─ Score 80-89?
  │  │  ├─ YES → MERGE: Move to done/, with notes
  │  │  └─ NO ↓
  │  │
  │  ├─ Score 70-79?
  │  │  ├─ YES → LEAD REVIEW: Manual verification required
  │  │  └─ NO ↓
  │  │
  │  ├─ Score 60-69?
  │  │  ├─ YES → REWORK: Create new DELEGATE with feedback
  │  │  │        (max 2 retries, then escalate)
  │  │  └─ NO ↓
  │  │
  │  └─ Score <60?
  │     └─ ESCALATE: Principal Engineer reviews
  │
  └─ Output: Routing decision, metrics recorded
```

---

## FAQ

**Q: What if a task fails at Gate 3 (DELEGATE validation)?**  
A: Orchestrator fixes the DELEGATE and resubmits. If issues persist, escalate to Senior Engineer.

**Q: What if an agent gets blocked at Gate 4?**  
A: Agent reports `status: blocked` in HANDBACK. Orchestrator escalates to Senior Engineer or Lead Engineer for unblocking.

**Q: What if HANDBACK scores 70-79?**  
A: Lead Engineer does manual code review. They can approve, conditionally approve, or request rework.

**Q: What if we need to bypass pre-commit hook?**  
A: Use `SKIP_HOOKS=1 git commit` with documented reason. Document in commit message why bypass was necessary.

**Q: Can we skip the pre-push gate?**  
A: Only in emergencies with `SKIP_HOOKS=1 git push`. Document reason and create follow-up task to fix root cause.

**Q: What happens if tests fail on pre-push?**  
A: It's a warning only — push proceeds. But fix tests before merging to main.

**Q: Who can authorize a bypass?**  
A: Lead Engineer or above. Document authorization in commit message.

---

## Update Log

- **2026-05-16:** Initial comprehensive workflow documentation with 7 gates, decision trees, escalation paths, and metrics collection.
