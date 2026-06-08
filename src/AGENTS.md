# Agent Roster & Handover Packet Protocol

> **Architecture:** Queue-based DELEGATE/HANDBACK — all work enters the queue; no direct agent-to-agent calls.  
> **Autonomy mode:** Reduced — agents pause when the queue is empty rather than inventing new work.  
> **Model selection:** Informed by the Model Engineer feedback loop; see [`src/skills/roles/model-engineer.md`](skills/roles/model-engineer.md).

---

## Philosophy

- **Queue-first** — every task enters `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` as a DELEGATE block; no ad-hoc delegation
- **enqueue() is mandatory** — ALL DELEGATEs and HANDBACKs MUST be created via `QueueOperations.enqueue()` (the `queue-management` skill). Direct file writes to any queue subdirectory (`incoming/`, `processing/`, `done/`, `failed/`) are forbidden and bypass schema validation.
- **Reduced autonomy** — agents pause when the queue is empty; they do NOT invent work
- **Start cheap, escalate deliberately** — route to the cheapest capable model; upgrade only when blocked
- **Root-cause fixes** — address the actual problem; never disable tests, add workarounds, or avoid failures
- **Cold-context agents** — every DELEGATE is self-contained; the receiving agent cannot rely on session state
- **Parallel by default** — the Orchestrator fans out multiple DELEGATEs simultaneously when tasks are independent
- **Token-conscious** — cite line numbers, suppress verbose output, trust tool confirmations; measure with Model Engineer

---

## Agent Roster

**MODEL NAMING (LOCKED):** All models use canonical format with DOTS: `claude-{variant}-{major}.{minor}`
(e.g., `claude-haiku-4.5`, `claude-sonnet-4.6`, `claude-opus-4.8`). See [SPEC.md > Model Naming Architecture](../SPEC.md).

| Role | Model | Effort | Multi-Model? | Use When |
|---|---|---|---|---|
| **Orchestrator** | claude-haiku-4.5 | low | — | All entry points; routing decisions; task management; metrics collection; model recommendations |
| **Engineer** | claude-haiku-4.5 | high | — | Well-scoped task with pre-written plan; low-medium complexity coding/implementation |
| **Quality Engineer** | claude-sonnet-4.6 | medium | — | Post-implementation quality gate; code review; model suitability assessment |
| **Senior Engineer** | claude-sonnet-4.5 | high | — | Complex coding tasks; implementation without fully pre-planned spec; diagnosis of root causes |
| **Lead Engineer** | claude-sonnet-4.6 | high | — | Code review; quality decisions; medium-complexity planning; architectural guidance |
| **Principal Engineer** | claude-opus-4.6 | high | 4.6/4.7/4.8 | Cross-service architecture; complex multi-step planning; design decisions affecting >2 repos |
| **Security Engineer** | claude-opus-4.8 | max | 4.8 only | Security analysis; threat modeling; vulnerability audits; final escalation path |
| **Model Engineer** | claude-sonnet-4.5 | high | — | Analyzes quality/cost feedback from QE; recommends optimal model/effort combinations for future similar tasks |

**Multi-Model column notes:**
- Principal Engineer: 4.6 (default/pure planning), 4.7 (design+execution), 4.8 (security-critical design). Orchestrator selects variant at DELEGATE-creation time. See [SPEC.md > Model Selection Architecture](../SPEC.md).
- Security Engineer: 4.8 always (non-downgrade rule). 4.7 only as emergency fallback if 4.8 unavailable; document in HANDBACK. See [SPEC.md > Model Selection Architecture](../SPEC.md).

### Cost Tiers

```
Tier 1 — Cheap (Haiku):   Orchestrator + Engineer          → $0.03–0.05/task
Tier 2 — Medium (Sonnet): Model Eng + QE + Lead + Senior   → $0.09/task
Tier 3 — Premium (Opus):  Principal + Security             → $0.15/task
```

**Rule:** Start cheap, escalate only when needed. The Orchestrator routes all work; it never implements.

---

## Orchestrator Entry Point

**All work flows through the Orchestrator.** The Orchestrator is your default handler and never performs implementation work itself—it routes, coordinates, and applies Model Engineer recommendations.

```
User request / External trigger
  └─► Orchestrator (haiku — cheap routing)
        ├─► Issues DELEGATE to the correct specialist
        ├─► Specialist performs work and returns HANDBACK
        └─► Orchestrator interprets result and coordinates next steps
```

**Why Orchestrator-first?**
- **Auditability** — all work is tracked as DELEGATE/HANDBACK blocks in the queue
- **Cost discipline** — starts cheap (Haiku), escalates only when needed
- **Protocol enforcement** — routing rules and model selection are consistent
- **Parallel execution** — independent tasks fan out simultaneously

Direct `@agent-name` invocation is available as an advanced escape hatch but skips protocol enforcement and audit trails. The canonical flow always goes through Orchestrator.

---

## Canonical DELEGATE/HANDBACK Schema

All work follows the DELEGATE/HANDBACK protocol. DELEGATEs are enqueued by the Orchestrator, processed by specialist agents, and HANDBACKs are returned with metrics.

### DELEGATE Format (Request)

```yaml
---
handoff_type: DELEGATE
agent: engineer                    # target specialist role (hyphenated)
task_id: unique-identifier
scope: "Clear, bounded description of what will be done (≥15 words)"
context:
  - "Relevant file: src/module.py (lines 45-67)"
  - "Error message or requirement summary"
plan:
  - "Step 1: Read and understand requirement"
  - "Step 2: Identify affected files"
  - "Step 3: Implement feature"
  - "Step 4: Run tests"
success_criteria:
  - "All tests pass"
  - "Code follows style guide"
  - "No linter warnings"
estimated_tokens: 1500
---
```

### HANDBACK Format (Response)

```yaml
---
handoff_type: HANDBACK
task_id: unique-identifier
status: success                    # success | failure | partial | blocked | escalate

output: |
  Modified src/module.py to implement feature. Added tests/test_feature.py
  with 100% coverage. All unit tests pass (47 tests). Code coverage: 92%.

metrics:
  quality: 0.95                    # 0.0-1.0 float
  tokens: 1200                     # total input + output
  cost: 0.019                      # USD
  duration_seconds: 42             # wall-clock time

confidence: 0.95                   # 0.0-1.0 float
---
```

---

## Multi-Model Selection (Tier 3)

Principal Engineer and Security Engineer support model variant selection based on task complexity.

**Decision criteria:**
- Principal Engineer: Use `claude-opus-4.6` for pure planning; `claude-opus-4.7` for cross-repo execution impact; `claude-opus-4.8` for security-critical design
- Security Engineer: Always use `claude-opus-4.8` (non-downgrade rule)

For detailed guidance, decision trees, and examples, see [SPEC.md > Model Selection Architecture](../SPEC.md).

---

## Delegation Model

```
User / External Trigger
  └─► Orchestrator  (haiku — cheap routing)
        ├─► Engineer               ← well-scoped tasks with full plans
        ├─► Senior Engineer        ← unscoped or multi-file work
        │     ├─► Lead Engineer    ← architecture decisions, code review
        │     ├─► Principal Eng    ← hard debugging, cross-service analysis
        │     └─► Security Eng     ← auth, crypto, threat modelling
        ├─► Quality Engineer       ← post-implementation validation (always)
        └─► Model Engineer         ← after QE HANDBACK, analyses metrics
```

### Routing Rules

1. **Security-scoped** → Security Engineer (always, no exceptions)
2. **Cross-service / architecture** → Principal Engineer
3. **Code review / validation** → Lead Engineer or Quality Engineer
4. **Unscoped complex work** → Senior Engineer (plan phase) → Engineer (execute phase)
5. **Well-scoped with plan** → Engineer
6. **Default** → Engineer with context

---

## Role Definitions

Detailed capabilities, boundaries, and escalation triggers for each role.

---

### 1. Orchestrator

**Model:** `claude-haiku-4.5`  **Tier:** Cheap  **Skill:** `src/skills/orchestration/task-routing.md`

**Purpose:** Entry point for all user requests. Routes work via the decision tree. Never implements.

**Capabilities:**
- Parse incoming requests and create DELEGATE blocks **via `queue-management` skill (`enqueue()`)**
- Route tasks to the correct role using routing rules above
- Fan out parallel DELEGATEs when tasks are independent
- Poll `~/.agentic-engineers/{session-id}/{harness}/queue/done/` for HANDBACKs and update `TODO.md`
- Re-delegate ESCALATION packets at the higher tier
- Summarise squad status as tables (not prose)

**MANDATORY — Creating DELEGATEs:**
All DELEGATEs MUST be created via `QueueOperations.enqueue()` from the `queue-management` skill.  
Direct file writes to queue directories are forbidden and bypass schema validation.

```python
# Correct — use enqueue() via queue-management skill
from skills.queue_management.scripts.queue_ops import QueueOperations
ops = QueueOperations(session_id=session_id)
ops.enqueue({
    "handoff_type": "DELEGATE",
    "task_id": "my-task-001",
    "agent": "engineer",         # NOT "role": "Engineer"
    "scope": "...",
    "plan": ["step 1 ...", "step 2 ..."],
    "context": "...",
    "success_criteria": ["criterion 1"],
})

# FORBIDDEN — never write directly to queue dirs
# open("~/.agentic-engineers/.../incoming/my-task.json", "w")  # NO
```

**Boundaries — Orchestrator MUST NOT:**
- Write code, edit files, or run tests
- Make architecture or security decisions
- Hold state across sessions (use `TODO.md` and the queue)
- Write DELEGATE or HANDBACK files directly to the queue directory (always use `enqueue()`)

**Escalation triggers:** None — the Orchestrator is the top of the routing chain. If the user's request requires human input (security/compliance critical, budget exceeded), pause and surface to the user.

**Pause condition:** Queue empty → Orchestrator PAUSES. Does not invent new work.

---

### 2. Engineer

**Model:** `claude-haiku-4.5`  **Tier:** Cheap  **Skill:** `src/skills/roles/engineer.md`

**Purpose:** Execute well-scoped tasks at known file:line addresses. Cheapest implementation role.

**Capabilities:**
- Single-file edits, straightforward multi-file edits (≤ 3 files, same package)
- Unit test writing (given a clear spec)
- Documentation updates at known locations
- Dependency version bumps
- Simple bug fixes with a clear root cause

**Boundaries — Engineer MUST NOT:**
- Read multiple related files to understand context before implementing
- Make architectural decisions or design choices
- Modify public API contracts without explicit instruction

**Escalation triggers:**
- Change touches > 3 files across different packages → **Senior Engineer**
- Requires reading multiple related files to understand context → **Senior Engineer**
- Test failures after 2 fix attempts → **Senior Engineer**
- Architecture or API design decision required → **Lead Engineer**
- Auth, crypto, secrets, or security implications discovered → **Security Engineer**

---

### 3. Senior Engineer

**Model:** `claude-sonnet-4.5`  **Tier:** Medium  **Skill:** `src/skills/roles/senior-engineer.md`

**Purpose:** Plans unscoped work; handles multi-file implementations requiring architectural awareness.

**Capabilities:**
- Read related files to understand context before implementing
- Multi-file refactoring and moderate-complexity implementations
- CI/CD pipeline changes
- Breaking dependency updates
- Code review of Engineer outputs when flagged by Quality Engineer

**Boundaries — Senior MUST NOT:**
- Make cross-repo API contract decisions
- Resolve architectural disagreements between services
- Conduct formal security audits

**Escalation triggers:**
- Architecture or API contract decisions required → **Lead Engineer**
- Cross-service or cross-repo coordination needed → **Lead Engineer**
- Debugging root cause spans > 2 services → **Principal Engineer**
- Hard problem with > 2 failed fix attempts → **Principal Engineer**
- Auth, crypto, token handling, or compliance implications → **Security Engineer**

---

### 4. Lead Engineer

**Model:** `claude-sonnet-4.6`  **Tier:** Medium  **Skill:** `src/skills/roles/lead-engineer.md`

**Purpose:** Architecture decisions, 8-point code review, API contract design, conflict resolution.

**Capabilities:**
- Make architecture decisions authoritatively (API contracts, domain boundaries, data models)
- Conduct 8-point code review (correctness, safety, patterns, performance, security surface, maintainability, test coverage, documentation)
- Resolve conflicts between competing design approaches
- Coordinate cross-repo work — ensure consistency across services
- Produce DELEGATE blocks for Engineer/Senior to implement decisions

**Boundaries — Lead MUST NOT:**
- Conduct formal threat modelling or vulnerability assessment
- Implement code changes (produce implementation DELEGATEs instead)

**Escalation triggers:**
- Fundamentally hard architectural problem with no clear solution → **Principal Engineer**
- Security-critical design decisions (auth flows, crypto selection) → **Security Engineer**
- Cross-repo coordination at a scale requiring principal-level analysis → **Principal Engineer**

---

### 5. Quality Engineer

**Model:** `claude-sonnet-4.6`  **Tier:** Medium  **Skill:** `src/skills/roles/quality-engineer.md`

**Purpose:** Post-implementation validation. Verifies HANDBACK correctness and assesses model suitability.

**Capabilities:**
- Validate acceptance criteria against delivered changes
- Run `CONFIG=dev make lint && make test && make build` and report results
- Assess whether the model/effort tier was appropriate for the task
- Populate `metrics.quality` in the HANDBACK (0.0–1.0 float)
- Flag regressions, missing tests, or inadequate implementation

**Boundaries — QE MUST NOT:**
- Implement fixes for discovered issues (produce DELEGATE blocks instead)
- Make architecture decisions

**Escalation triggers:**
- Persistent build/lint failures after 2 re-run attempts → **Lead Engineer**
- Security-related failure patterns discovered → **Security Engineer**
- Systemic failure pattern across multiple tasks → **Principal Engineer**

---

### 6. Model Engineer

**Model:** `claude-sonnet-4.5`  **Tier:** Medium  **Skill:** `src/skills/roles/model-engineer.md`

**Purpose:** Analyse HANDBACK efficiency metrics; recommend model or effort tier adjustments.

**Capabilities:**
- Parse HANDBACK `metrics` blocks (tokens, cost, quality, duration_seconds)
- Compare actual vs. estimated token usage across task history
- Recommend model downgrade (cost saving) or upgrade (quality improvement)
- Identify effort-level mismatches (task was too small/large for the assigned tier)
- Write recommendations to `src/TOKEN_METRICS.md` in standardised format

**Boundaries — Model Engineer MUST NOT:**
- Implement code changes
- Approve or reject tasks — recommendations only

**Escalation triggers:**
- System-level quality regression spanning multiple roles → **Principal Engineer**
- Contested metrics recommendation → **Lead Engineer**

---

### 7. Principal Engineer

**Model:** `claude-opus-4-6`  **Tier:** Premium  **Skill:** `src/skills/roles/principal-engineer.md`

**Purpose:** Cross-service architecture, hard debugging, critical design decisions. Escalation only.

**Capabilities:**
- Root cause analysis spanning deep stack traces or multiple services
- Complex architectural analysis (data flow, race conditions, distributed system semantics)
- Hard debugging where Senior has made ≥ 2 failed attempts
- Critical design decisions that Lead cannot resolve
- Produce structured findings with exact file:line references
- Generate DELEGATE blocks for Engineer/Senior to implement findings

**Boundaries — Principal MUST NOT:**
- Implement fixes (findings → DELEGATEs for cheaper tiers)
- Conduct formal security audits (→ Security Engineer)

**Escalation triggers:**
- Security-critical design decisions (auth, encryption, key management) → **Security Engineer**
- Principal is the top of the non-security chain; if blocked, surface to user

---

### 8. Security Engineer

**Model:** `claude-opus-4.8`  **Tier:** Premium  **Skill:** `src/skills/roles/security-engineer.md`

**Purpose:** Threat modelling, vulnerability assessment, compliance review. Always assigned for security-scoped work.

**Capabilities:**
- Formal threat modelling (STRIDE, attack surface analysis)
- Vulnerability assessment (OWASP Top 10, injection, broken auth, secrets exposure)
- Compliance review (OAuth 2.0, zero-trust, secrets handling, GDPR surface)
- CLI permission policy review
- Produce findings table (severity, file:line, description, recommendation)
- Generate DELEGATE blocks for Engineer/Senior to implement fixes

**Boundaries — Security Engineer MUST NOT:**
- Implement fixes (findings → DELEGATEs for cheaper tiers)
- Be skipped for any auth/crypto/secrets/compliance task

**Escalation triggers:**
- Security Engineer is the top of the security chain. Surface to user if findings require
  executive decision or external compliance sign-off.

---

## Handover Packet Protocol

All work is delegated via a **DELEGATE block** written to `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-NNN.yaml`.  
On completion, agents return a **HANDBACK block** to `~/.agentic-engineers/{session-id}/{harness}/queue/done/TASK-NNN-handback.yaml`.

### DELEGATE Block Format

> **Canonical schema:** `docs/specs/protocol-core-v1.0.yaml` (single source of truth)  
> **Deprecated:** `type: DELEGATE` — use `handoff_type: DELEGATE` instead. Files using `type:` will pass with a deprecation warning; the field will become an error in the next major version.

```yaml
# File: ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-NNN.yaml
---
task_id: my-task-identifier    # kebab-case, 3-50 chars (^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$)
handoff_type: DELEGATE         # canonical discriminator (NOT type:)
agent: senior-engineer         # hyphenated role name — see VALID_AGENTS below
skill: senior-engineer         # skill name resolving to src/skills/<skill>/
model: claude-sonnet-4.6       # must be explicit — no implicit defaults
effort: high                   # low | medium | high

scope: |
  One sentence or paragraph describing what will be done, to what, and
  explicit out-of-scope boundaries. Must be >= 15 words.

context:
  - "Relevant file: path/to/relevant/file.py (lines 45-67)"
  - "Repo: github.com/owner/repo-name, branch: feature/branch-name"
  - "Root cause: describe the problem and why this approach solves it"

plan:
  - "Step 1: Read and understand the relevant files"
  - "Step 2: Implement the required changes"
  - "Step 3: Write or update tests (TDD: Red → Green)"
  - "Step 4: Verify with repro command"

success_criteria:
  - "AC1: describe what done looks like"
  - "AC2: describe measurable outcome"
  - "AC3: repro command passes with no failures"

# --- Optional extension fields (forward-compatible) ---
tokens_estimate: 8000          # estimated max tokens for this task
budget: 0.09                   # $ ceiling based on model + estimate
priority: 5                    # 1 (lowest) - 10 (highest)
deadline: "2026-06-08T18:00:00Z"
dependencies: []               # task_ids that must complete first
```

> **Required core fields:** `task_id`, `handoff_type`, `agent`, `skill`, `scope` (>=15 words),
> `plan` (>=2 steps, each >=3 words), `success_criteria` (>=1 item), `context` (>=20 words or non-empty array).  
>
> **Valid agents:** `orchestrator`, `engineer`, `senior-engineer`, `lead-engineer`,
> `principal-engineer`, `security-engineer`, `quality-engineer`, `model-engineer`
> (hyphens only — `senior_engineer` with underscores is invalid).

### HANDBACK Block Format

Canonical schema: [`docs/specs/protocol-core-v1.0.yaml`](../docs/specs/protocol-core-v1.0.yaml).
Required core fields: `task_id`, `status`, `output`, `metrics` (with `quality`, `tokens`, `cost`, `duration_seconds`).

> **Deprecated:** `type: HANDBACK` — use `handoff_type: HANDBACK` instead (same migration as DELEGATE).

```yaml
# File: ~/.agentic-engineers/{session-id}/{harness}/queue/done/TASK-NNN-handback.yaml
---
task_id: my-task-identifier    # must match the originating DELEGATE's task_id
handoff_type: HANDBACK         # canonical discriminator (NOT type:)
status: success                # success | failure | partial | blocked | escalate

output: |
  One-paragraph summary of what was done, files changed, and key decisions.
  e.g. "Modified path/to/file.py (lines 45-67) and path/to/other.ts (12-30);
  AC1-AC3 PASS via make verify."

metrics:                       # ALL four sub-fields are REQUIRED
  quality: 0.88                # float 0.0–1.0, self-assessed delivery quality
  tokens: 5840                 # non-negative int, total tokens (input + output)
  cost: 0.09                   # non-negative float, USD
  duration_seconds: 42         # non-negative float, wall-clock execution seconds

# --- Optional extension fields (forward-compatible) ---
model_used: claude-sonnet-4.6
effort_actual: medium
confidence: 0.9                # 0.0–1.0
escalations: 0
flags: []                      # advisory flags / anomalies
error: null                    # error detail when status is failure or blocked
escalation: null               # or ESCALATION block (see below) if status: escalate
```

> **Status values:** `success` (all criteria met), `failure` (criteria not met),
> `partial` (some criteria met), `blocked` (external dependency needed),
> `escalate` (requires higher-tier agent or human decision).  
> **Invalid statuses:** `complete` and `failed` are NOT valid — use `success` and `failure`.  
>
> **metrics sub-fields** (all required — no omissions accepted):  
> - `quality`: float 0.0–1.0 (self-assessed quality of delivered work)  
> - `tokens`: non-negative integer (total input + output tokens consumed)  
> - `cost`: non-negative float (USD monetary cost)  
> - `duration_seconds`: non-negative float (wall-clock execution time)

### ESCALATION Packet Format

When an agent hits an escalation trigger, it MUST stop implementation work and emit:

```yaml
# Embedded in HANDBACK under the `escalation:` key, or as a standalone file
---
task_id: my-task-identifier
type: ESCALATION              # ESCALATION packets retain type: (not a DELEGATE/HANDBACK)
from_role: senior-engineer
to_role: principal-engineer
reason: |
  Root cause spans multiple services — requires cross-service analysis
  beyond Senior's authority. Specifically: [details of what was tried and why it failed]

findings_so_far: |
  Summary of what was discovered before escalation, so the receiving
  agent starts with full context and does not re-investigate the same ground.

recommended_focus:
  - Specific area 1 to investigate
  - Specific area 2 to investigate
```

The Orchestrator reads this ESCALATION block from the HANDBACK, creates a new DELEGATE block
targeting `to_role` (using `handoff_type: DELEGATE` and `agent: principal-engineer`) with the
escalation content inlined in `context`.

---

## ACK Protocol

Every agent MUST emit an ACK as its **first output** before performing any work.

### Standard ACK

```
✅ [Role Name] ACK — [TASK-ID]
```

### Blocked ACK (missing context)

```
⚠️ [Role Name] BLOCKED — [TASK-ID]
Missing: [list of what's missing or unclear]
Request: [what information is needed to proceed]
```

### Model Mismatch

If the agent detects it is running on a different model than specified in the DELEGATE `model:` field:

```
❌ MODEL_MISMATCH — expected claude-sonnet-4.6, got claude-haiku-4.5
Stopping. Orchestrator must re-delegate with the correct model.
```

### Completion Footer

Every agent MUST include in its final output:

```
MODEL_USED: claude-sonnet-4.6   # actual model used (not the requested model)
```

---

## Queue-Based Execution Model

### Full Flow

```
1.  User drops DELEGATE into ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-NNN.yaml
    (or Orchestrator generates DELEGATE from a user request)

2.  Orchestrator polls queue → reads TASK-NNN.yaml → applies routing rules

3.  Orchestrator fans out DELEGATEs for independent tasks in parallel

4.  Each agent:
      a. ACKs the task (first output)
      b. Loads its skill file from skill_refs
      c. Performs work
      d. Writes HANDBACK to ~/.agentic-engineers/{session-id}/{harness}/queue/done/TASK-NNN-handback.yaml

5.  Quality Engineer validates the HANDBACK:
      - Checks acceptance_criteria are met
      - Runs repro command to verify
      - Populates metrics.quality (0.0–1.0) in the HANDBACK

6.  Model Engineer analyses HANDBACK metrics:
      - Compares tokens used vs. estimated across task history
      - Emits model/effort recommendation if drift detected

7.  Orchestrator reads HANDBACK status:
      - COMPLETE   → mark TASK-NNN done in TODO.md
      - PARTIAL    → re-delegate remaining work
      - BLOCKED    → surface to user with blocker detail
      - ESCALATE   → re-delegate ESCALATION block at higher tier

8.  If queue empty → Orchestrator PAUSES
```

### Pause Condition

The Orchestrator **pauses** when `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` is empty.  
It does NOT invent new work. This is by design — reduced autonomy prevents runaway scope.

To resume: write a new DELEGATE block to the queue, or add a task to `TODO.md`.

---

## Example Workflows

### Example 1 — Simple File Edit (Engineer)

```yaml
# ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-101.yaml
---
task_id: task-101-postal-validation
handoff_type: DELEGATE
agent: engineer
skill: engineer
model: claude-haiku-4.5
effort: low

scope: |
  Add AU PostalCode validation rule to address validator in src/validation/postal.py.
  PostalCode is optional but when present must be exactly 4 digits. Out of scope:
  any changes to the validator public interface or other validation rules.

context:
  - "File: src/validation/postal.py (lines 12-34) — add 4-digit AU postcode regex rule"
  - "File: tests/test_postal.py — add unit tests for valid and invalid postcodes"
  - "Repo: github.com/niallyoung/payments-service, branch: feature/postal-validation"

plan:
  - "Step 1: Read src/validation/postal.py (lines 12-34) to understand existing rule structure"
  - "Step 2: Add AU_POSTCODE_REGEX and PostalCodeValidator at line 15 (4 digits only)"
  - "Step 3: Write tests for valid ('2000', '0800') and invalid ('ABC', '123', '12345') cases"
  - "Step 4: Run make test FILTER=test_postal and verify 0 failures"

success_criteria:
  - "AC1: PostalCode '2000' and '0800' pass validation"
  - "AC2: PostalCode 'ABC', '123', '12345' are rejected with a clear error message"
  - "AC3: make test FILTER=test_postal passes with no failures"

tokens_estimate: 2000
budget: 0.03
```

**Agent output:**

```
✅ Engineer ACK — TASK-101

[implements postal.py and test_postal.py changes]

Changes:
- src/validation/postal.py:15 — added AU_POSTCODE_REGEX and PostalCodeValidator rule
- tests/test_postal.py:1-28 — added tests for valid/invalid AU postcodes

CI: PASS — make test FILTER=test_postal: 6 passed
MODEL_USED: claude-haiku-4.5
```

---

### Example 2 — Escalation Chain (Engineer → Senior → Lead)

**Step 1: Engineer hits escalation trigger**

```yaml
# HANDBACK from Engineer
---
task_id: task-202-payment-refactor
handoff_type: HANDBACK
status: escalate

output: |
  Payment refactor requires changes to 5 files across payment/ and checkout/ packages.
  This exceeds the 3-file boundary for Engineer. API contract between the two domains
  needs a decision before implementation.

metrics:
  quality: 0.0
  tokens: 1200
  cost: 0.02
  duration_seconds: 18

escalation:
  task_id: task-202-payment-refactor
  type: ESCALATION
  from_role: engineer
  to_role: senior-engineer
  reason: |
    Change touches 5 files in 2 packages (payment/, checkout/).
    Architectural boundary between payment and checkout domains needs
    clarification before implementation can proceed.
  findings_so_far: |
    payment/processor.py:45-67 needs new checkout_id param.
    checkout/domain.py:12-30 needs a PaymentRef type.
    Both changes affect the public API contract.
  recommended_focus:
    - Define PaymentRef type boundary (checkout-owned vs payment-owned)
    - Confirm API contract for processor.create_payment(checkout_id)
```

**Step 2: Orchestrator re-delegates to Senior Engineer**

```yaml
# ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-202-senior.yaml
---
task_id: task-202-senior-payment-arch
handoff_type: DELEGATE
agent: senior-engineer
skill: senior-engineer
model: claude-sonnet-4.6
effort: high

scope: |
  Determine PaymentRef type ownership (checkout/ vs payment/ package) and define the
  processor.create_payment(checkout_id) API contract. Engineer escalated TASK-202 because
  the refactor touches 5 files across two domain packages. Out of scope: implementation
  (produce DELEGATE blocks for Engineer to implement the decided design).

context:
  - "Escalation from task-202-payment-refactor: payment refactor touches 5 files in 2 packages"
  - "File: src/payment/processor.py (lines 45-67) — needs new checkout_id param"
  - "File: src/checkout/domain.py (lines 12-30) — needs a PaymentRef type"
  - "Repo: github.com/niallyoung/payments-service, branch: feature/payment-refactor"
  - "Root cause: Both changes affect the public API contract; domain boundary unclear"

plan:
  - "Step 1: Read payment/processor.py:45-67 and checkout/domain.py:12-30 to understand current boundaries"
  - "Step 2: Determine if PaymentRef belongs in checkout/ (checkout-owned) or payment/ (payment-owned)"
  - "Step 3: Define the processor.create_payment(checkout_id) API contract"
  - "Step 4: Produce DELEGATE blocks for Engineer to implement the decided contract"
  - "Step 5: Escalate to Lead Engineer if API contract decision exceeds Senior's authority"

success_criteria:
  - "AC1: PaymentRef type ownership is decided and documented"
  - "AC2: processor.create_payment API contract is defined with the checkout_id parameter"
  - "AC3: Implementation DELEGATEs produced for Engineer (or escalated to Lead)"

tokens_estimate: 8000
budget: 0.09
```

**Step 3: Senior hits arch escalation trigger → escalates to Lead**

Senior reads related files, determines the PaymentRef type crosses a domain boundary that
requires an explicit API contract decision, and emits a HANDBACK with `status: escalate`
targeting Lead Engineer — including its analysis as `findings_so_far`.

**Step 4: Lead makes the decision, produces implementation DELEGATEs**

Lead Engineer emits an architecture decision document and two DELEGATE blocks:
one targeting Senior to implement the `PaymentRef` type, one targeting Engineer for
the updated `processor.py` call site.

---

### Example 3 — Security Audit (Security Engineer)

```yaml
# ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-303.yaml
---
task_id: task-303-jwt-refresh-audit
handoff_type: DELEGATE
agent: security-engineer
skill: security-engineer
model: claude-opus-4.8
effort: high

scope: |
  Audit the JWT refresh token flow in auth-service for vulnerabilities before shipping.
  The feature introduces sliding-window refresh: access tokens are transparently reissued
  within a 15-minute window. Audit replay attacks, missing expiry checks, and insecure
  token storage patterns. Out of scope: implementing fixes (produce DELEGATE blocks instead).

context:
  - "File: src/auth/middleware.py (lines 45-89) — token validation middleware"
  - "File: src/auth/tokens.py (lines 10-60) — token issuance and expiry logic"
  - "File: src/auth/handlers.py (lines 120-175) — refresh token redemption handler"
  - "Repo: github.com/niallyoung/auth-service, branch: feature/jwt-refresh"
  - "Concern: replay attacks on the sliding-window refresh window; missing exp validation; localStorage storage"

plan:
  - "Step 1: Read middleware.py:45-89, tokens.py:10-60, handlers.py:120-175"
  - "Step 2: Identify replay attack vectors in the sliding-window refresh flow"
  - "Step 3: Check that exp claim is validated at every token issuance and redemption path"
  - "Step 4: Review token storage patterns for secrets exposure (httpOnly cookie vs localStorage)"
  - "Step 5: Produce findings table (severity, file:line, description, recommendation)"
  - "Step 6: Produce DELEGATE blocks for Engineer/Senior to implement each finding"

success_criteria:
  - "AC1: Findings table produced (severity, file:line, description, recommendation)"
  - "AC2: DELEGATE blocks produced for each finding requiring a fix"
  - "AC3: No CRITICAL or HIGH findings left without an implementation DELEGATE"

tokens_estimate: 12000
budget: 0.15
```

**Expected output format:**

```
✅ Security Engineer ACK — TASK-303

## Findings

| Severity | File:Line | Issue | Recommendation |
|----------|-----------|-------|----------------|
| CRITICAL | src/auth/tokens.py:34 | exp claim not validated on refresh | Validate exp before issuing new token |
| HIGH     | src/auth/handlers.py:142 | refresh token not invalidated after use | Add jti blacklist on redemption |
| MEDIUM   | src/auth/middleware.py:61 | token stored in localStorage | Move to httpOnly cookie |

## Implementation DELEGATEs

[DELEGATE block for Engineer — fix exp validation at tokens.py:34]
[DELEGATE block for Senior — implement jti blacklist in handlers.py]
[DELEGATE block for Engineer — update token storage in middleware.py]

MODEL_USED: claude-opus-4.8
```

---

### Example 4 — Post-Implementation Validation (Quality Engineer)

```yaml
# ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/TASK-404-qe.yaml
---
task_id: task-404-qe-address-validation
handoff_type: DELEGATE
agent: quality-engineer
skill: quality-engineer
model: claude-sonnet-4.6
effort: medium

scope: |
  Validate the HANDBACK from task-404 (Senior Engineer refactored address validation
  module: 3 files, 87 lines changed). Verify all acceptance criteria are met, run the
  test suite, and assess whether the assigned model was appropriate for the task.
  Out of scope: implementing fixes — produce DELEGATE blocks if issues are found.

context:
  - "HANDBACK to validate: task-404 (Senior Engineer, address validation refactor)"
  - "Files changed: src/validation/address.py, src/validation/postal.py, tests/test_address.py"
  - "Repo: github.com/niallyoung/validation-service, branch: feature/address-refactor"
  - "Repro command: CONFIG=dev make lint && CONFIG=dev make test && CONFIG=dev make build"

plan:
  - "Step 1: Run CONFIG=dev make lint — verify 0 errors"
  - "Step 2: Run CONFIG=dev make test — verify all address tests green"
  - "Step 3: Run CONFIG=dev make build — verify successful build"
  - "Step 4: Verify each AC from task-404 against delivered changes"
  - "Step 5: Assess model suitability (was claude-sonnet-4.6 appropriate or would haiku suffice?)"
  - "Step 6: Populate metrics block in HANDBACK with quality score and assessment"

success_criteria:
  - "AC1: make lint passes with no errors"
  - "AC2: make test passes, all address tests green"
  - "AC3: make build succeeds"
  - "AC4: metrics block in HANDBACK populated with quality (0.0-1.0), tokens, cost, duration_seconds"

tokens_estimate: 4000
budget: 0.09
```

---

## Role Summary Table

| Role | Skill File | When to Use | Escalates To |
|------|-----------|-------------|--------------|
| Orchestrator | `src/skills/orchestration/task-routing.md` | All task entry points | User (for critical decisions) |
| Engineer | `src/skills/roles/engineer.md` | Scoped tasks, file edits, tests | Senior / Lead / Security |
| Senior Engineer | `src/skills/roles/senior-engineer.md` | Planning, multi-file changes | Lead / Principal / Security |
| Lead Engineer | `src/skills/roles/lead-engineer.md` | Code review, arch guidance | Principal / Security |
| Quality Engineer | `src/skills/roles/quality-engineer.md` | Post-implementation validation | Lead / Security / Principal |
| Model Engineer | `src/skills/roles/model-engineer.md` | After QE HANDBACK with metrics | Lead / Principal |
| Principal Engineer | `src/skills/roles/principal-engineer.md` | Hard bugs, cross-service design | Security / User |
| Security Engineer | `src/skills/roles/security-engineer.md` | All security-scoped work | User |

---

## Token Burn Reduction

- **Summarise, don't recap** — post findings as tables, not prose
- **Stay thin** — Orchestrator reads HANDBACK summaries only, not full outputs
- **No context spillover** — each DELEGATE is self-contained; receiving agent has no session state
- **Cite line numbers** — engineers work at the addresses given; no exploring
- **Chain bash commands** — use `&&` to combine related operations
- **Trust tool confirmations** — never re-read a file you just edited
- **Grep before view** — find exact lines first, then `view_range` only that section
- **Model Engineer feedback loop** — use token usage trends to downgrade over-provisioned roles

> For full cost tracking spec, see [`src/TOKEN_METRICS.md`](TOKEN_METRICS.md).
