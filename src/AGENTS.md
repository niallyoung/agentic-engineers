# Agent Roster & Handover Packet Protocol

> **Architecture:** Queue-based DELEGATE/HANDBACK — all work enters the queue; no direct agent-to-agent calls.  
> **Autonomy mode:** Reduced — agents pause when the queue is empty rather than inventing new work.  
> **Model selection:** Informed by the Model Engineer feedback loop; see [`src/skills/roles/model-engineer.md`](skills/roles/model-engineer.md).

---

## Philosophy

- **Queue-first** — every task enters `~/.copilot/queue/incoming/` as a DELEGATE block; no ad-hoc delegation
- **Reduced autonomy** — agents pause when the queue is empty; they do NOT invent work
- **Start cheap, escalate deliberately** — route to the cheapest capable model; upgrade only when blocked
- **Root-cause fixes** — address the actual problem; never disable tests, add workarounds, or avoid failures
- **Cold-context agents** — every DELEGATE is self-contained; the receiving agent cannot rely on session state
- **Parallel by default** — the Orchestrator fans out multiple DELEGATEs simultaneously when tasks are independent
- **Token-conscious** — cite line numbers, suppress verbose output, trust tool confirmations; measure with Model Engineer

---

## Agent Roster

| # | Role | Model | Thinking | Cost/Task | Purpose |
|---|------|-------|----------|-----------|---------|
| 1 | **Orchestrator** | `claude-haiku-4-5` | ❌ | $0.03 | Entry point — routes all work via decision tree, never does implementation |
| 2 | **Engineer** | `claude-haiku-4-5` | ❌ | $0.05 | Executes well-scoped, pre-planned tasks (file edits, tests, simple fixes) |
| 3 | **Model Engineer** | `claude-sonnet-4-6` | ✅ | $0.09 | Analyses HANDBACK metrics; recommends model/effort adjustments |
| 4 | **Quality Engineer** | `claude-sonnet-4-6` | ✅ | $0.09 | Post-implementation validation; model suitability assessment |
| 5 | **Lead Engineer** | `claude-sonnet-4-6` | ✅ | $0.09 | 8-point code review; architectural guidance; conflict resolution |
| 6 | **Senior Engineer** | `claude-sonnet-4-6` | ✅ | $0.09 | Plans unscoped work; multi-file implementations; moderate-complexity |
| 7 | **Principal Engineer** | `claude-opus-4-6` | ✅ | $0.15 | Cross-service architecture; hard debugging; critical design decisions |
| 8 | **Security Engineer** | `claude-opus-4-7` | ✅ | $0.15 | Threat modelling; vulnerability assessment; compliance review |

### Cost Tiers

```
Tier 1 — Cheap (Haiku):   Orchestrator + Engineer          → $0.03–0.05/task
Tier 2 — Medium (Sonnet): Model Eng + QE + Lead + Senior   → $0.09/task
Tier 3 — Premium (Opus):  Principal + Security             → $0.15/task
```

**Rule:** Start cheap, escalate only when needed. The Orchestrator routes all work; it never implements.

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

**Model:** `claude-haiku-4-5`  **Tier:** Cheap  **Skill:** `src/skills/orchestration/task-routing.md`

**Purpose:** Entry point for all user requests. Routes work via the decision tree. Never implements.

**Capabilities:**
- Parse incoming requests and create DELEGATE blocks
- Route tasks to the correct role using routing rules above
- Fan out parallel DELEGATEs when tasks are independent
- Poll `~/.copilot/queue/done/` for HANDBACKs and update `TODO.md`
- Re-delegate ESCALATION packets at the higher tier
- Summarise squad status as tables (not prose)

**Boundaries — Orchestrator MUST NOT:**
- Write code, edit files, or run tests
- Make architecture or security decisions
- Hold state across sessions (use `TODO.md` and the queue)

**Escalation triggers:** None — the Orchestrator is the top of the routing chain. If the user's request requires human input (security/compliance critical, budget exceeded), pause and surface to the user.

**Pause condition:** Queue empty → Orchestrator PAUSES. Does not invent new work.

---

### 2. Engineer

**Model:** `claude-haiku-4-5`  **Tier:** Cheap  **Skill:** `src/skills/roles/engineer.md`

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

**Model:** `claude-sonnet-4-6`  **Tier:** Medium  **Skill:** `src/skills/roles/senior-engineer.md`

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

**Model:** `claude-sonnet-4-6`  **Tier:** Medium  **Skill:** `src/skills/roles/lead-engineer.md`

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

**Model:** `claude-sonnet-4-6`  **Tier:** Medium  **Skill:** `src/skills/roles/quality-engineer.md`

**Purpose:** Post-implementation validation. Verifies HANDBACK correctness and assesses model suitability.

**Capabilities:**
- Validate acceptance criteria against delivered changes
- Run `CONFIG=dev make lint && make test && make build` and report results
- Assess whether the model/effort tier was appropriate for the task
- Populate `metrics.quality_score` in the HANDBACK
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

**Model:** `claude-sonnet-4-6`  **Tier:** Medium  **Skill:** `src/skills/roles/model-engineer.md`

**Purpose:** Analyse HANDBACK efficiency metrics; recommend model or effort tier adjustments.

**Capabilities:**
- Parse HANDBACK `metrics` blocks (tokens_used, efficiency_ratio, quality_score, duration_ms)
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

**Model:** `claude-opus-4-7`  **Tier:** Premium  **Skill:** `src/skills/roles/security-engineer.md`

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

All work is delegated via a **DELEGATE block** written to `~/.copilot/queue/incoming/TASK-NNN.yaml`.  
On completion, agents return a **HANDBACK block** to `~/.copilot/queue/done/TASK-NNN-handback.yaml`.

### DELEGATE Block Format

```yaml
# File: ~/.copilot/queue/incoming/TASK-NNN.yaml
---
task_id: TASK-NNN
type: DELEGATE
role: senior-engineer          # target role (lowercase-hyphenated)
model: claude-sonnet-4-6       # must be explicit — no implicit defaults
effort: high                   # low | medium | high | max
priority: normal               # low | normal | high | urgent

context:
  description: |
    One-paragraph description of what needs to be done and why.
  repo: owner/repo-name
  branch: feature/branch-name
  commit: HEAD                 # SHA or HEAD
  files:
    - path/to/relevant/file.py
    - path/to/other/file.ts
  line_refs:
    - "path/to/file.py:45-67"

requirements:
  - Specific requirement 1
  - Specific requirement 2
  - Specific requirement 3

acceptance_criteria:
  - "AC1: describe what done looks like"
  - "AC2: describe measurable outcome"
  - "AC3: how to verify it worked"

constraints:
  - "Do not modify the public API"
  - "Keep backward compatibility"

escalation_triggers:
  - "Change touches > 3 files in different packages → Senior Engineer"
  - "Test failures after 2 fix attempts → Senior Engineer"

repro: "make test FILTER=TestPostalCode"   # command to verify the task

skill_refs:
  - src/skills/roles/senior-engineer.md
  - src/skills/patterns/implementation-coding.md

token_budget: 8000             # estimated max tokens for this task
estimated_cost: 0.09           # $ estimate based on model + budget
```

> **Required fields:** `task_id`, `type`, `role`, `model`, `context.description`, `context.repo`,
> `context.branch`, `context.commit`, `acceptance_criteria`, `escalation_triggers`, `repro`, `skill_refs`.  
> All other fields are strongly recommended but optional.

### HANDBACK Block Format

```yaml
# File: ~/.copilot/queue/done/TASK-NNN-handback.yaml
---
task_id: TASK-NNN
type: HANDBACK
role: senior-engineer
status: COMPLETE               # COMPLETE | PARTIAL | BLOCKED | ESCALATE

summary: |
  One-paragraph summary of what was done and any important decisions made.

changes:
  - file: path/to/file.py
    lines: "45-67"
    description: What changed and why
  - file: path/to/other/file.ts
    lines: "12-30"
    description: What changed and why

acceptance_verified:
  - "AC1: PASS — description of how verified"
  - "AC2: PASS — test output confirms"
  - "AC3: PASS — ran make verify"

metrics:
  tokens_used: 5840
  tokens_estimated: 8000
  efficiency_ratio: 0.73       # tokens_used / tokens_estimated
  model_used: claude-sonnet-4-6
  duration_ms: 42000
  quality_score: 0.88          # 0.0–1.0, self-assessed

issues: []                     # list any blockers or anomalies

escalation: null               # or ESCALATION block (see below) if status: ESCALATE
```

### ESCALATION Packet Format

When an agent hits an escalation trigger, it MUST stop implementation work and emit:

```yaml
# Embedded in HANDBACK under the `escalation:` key, or as a standalone file
---
task_id: TASK-NNN
type: ESCALATION
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

skill_refs:
  - src/skills/roles/principal-engineer.md
```

The Orchestrator reads this ESCALATION block from the HANDBACK, creates a new DELEGATE block
targeting `to_role` with the escalation content inlined in `context.description`.

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
❌ MODEL_MISMATCH — expected claude-sonnet-4-6, got claude-haiku-4-5
Stopping. Orchestrator must re-delegate with the correct model.
```

### Completion Footer

Every agent MUST include in its final output:

```
MODEL_USED: claude-sonnet-4-6   # actual model used (not the requested model)
```

---

## Queue-Based Execution Model

### Full Flow

```
1.  User drops DELEGATE into ~/.copilot/queue/incoming/TASK-NNN.yaml
    (or Orchestrator generates DELEGATE from a user request)

2.  Orchestrator polls queue → reads TASK-NNN.yaml → applies routing rules

3.  Orchestrator fans out DELEGATEs for independent tasks in parallel

4.  Each agent:
      a. ACKs the task (first output)
      b. Loads its skill file from skill_refs
      c. Performs work
      d. Writes HANDBACK to ~/.copilot/queue/done/TASK-NNN-handback.yaml

5.  Quality Engineer validates the HANDBACK:
      - Checks acceptance_criteria are met
      - Runs repro command to verify
      - Writes quality_score into metrics

6.  Model Engineer analyses HANDBACK metrics:
      - Compares efficiency_ratio vs. baseline
      - Emits model/effort recommendation if drift detected

7.  Orchestrator reads HANDBACK status:
      - COMPLETE   → mark TASK-NNN done in TODO.md
      - PARTIAL    → re-delegate remaining work
      - BLOCKED    → surface to user with blocker detail
      - ESCALATE   → re-delegate ESCALATION block at higher tier

8.  If queue empty → Orchestrator PAUSES
```

### Pause Condition

The Orchestrator **pauses** when `~/.copilot/queue/incoming/` is empty.  
It does NOT invent new work. This is by design — reduced autonomy prevents runaway scope.

To resume: write a new DELEGATE block to the queue, or add a task to `TODO.md`.

---

## Example Workflows

### Example 1 — Simple File Edit (Engineer)

```yaml
# ~/.copilot/queue/incoming/TASK-101.yaml
---
task_id: TASK-101
type: DELEGATE
role: engineer
model: claude-haiku-4-5
effort: low
priority: normal

context:
  description: |
    Add AU PostalCode validation rule to the address validator.
    PostalCode is optional but when present must be exactly 4 digits.
  repo: niall/payments-service
  branch: feature/postal-validation
  commit: HEAD
  files:
    - src/validation/postal.py
    - tests/test_postal.py
  line_refs:
    - "src/validation/postal.py:12-34"

requirements:
  - Add 4-digit AU postcode regex rule
  - Add unit tests for valid and invalid cases

acceptance_criteria:
  - "AC1: PostalCode '2000' and '0800' pass validation"
  - "AC2: PostalCode 'ABC', '123', '12345' are rejected with a clear error message"
  - "AC3: make test FILTER=test_postal passes with no failures"

constraints:
  - "Do not change the validator's public interface"

escalation_triggers:
  - "Change touches > 3 files in different packages → Senior Engineer"
  - "Test failures after 2 fix attempts → Senior Engineer"

repro: "make test FILTER=test_postal"

skill_refs:
  - src/skills/roles/engineer.md

token_budget: 2000
estimated_cost: 0.03
```

**Agent output:**

```
✅ Engineer ACK — TASK-101

[implements postal.py and test_postal.py changes]

Changes:
- src/validation/postal.py:15 — added AU_POSTCODE_REGEX and PostalCodeValidator rule
- tests/test_postal.py:1-28 — added tests for valid/invalid AU postcodes

CI: PASS — make test FILTER=test_postal: 6 passed
MODEL_USED: claude-haiku-4-5
```

---

### Example 2 — Escalation Chain (Engineer → Senior → Lead)

**Step 1: Engineer hits escalation trigger**

```yaml
# HANDBACK from Engineer
---
task_id: TASK-202
type: HANDBACK
role: engineer
status: ESCALATE

summary: |
  Payment refactor requires changes to 5 files across payment/ and checkout/ packages.
  This exceeds the 3-file boundary for Engineer. API contract between the two domains
  needs a decision before implementation.

metrics:
  tokens_used: 1200
  tokens_estimated: 2000
  efficiency_ratio: 0.60
  model_used: claude-haiku-4-5
  duration_ms: 8000
  quality_score: 0.0

escalation:
  task_id: TASK-202
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
  skill_refs:
    - src/skills/roles/senior-engineer.md
```

**Step 2: Orchestrator re-delegates to Senior Engineer**

```yaml
# ~/.copilot/queue/incoming/TASK-202-senior.yaml
---
task_id: TASK-202-senior
type: DELEGATE
role: senior-engineer
model: claude-sonnet-4-6
effort: high
priority: normal

context:
  description: |
    Engineer escalated TASK-202 — payment refactor touches 5 files across payment/
    and checkout/ packages. Architectural boundary needs to be determined before
    implementation. Senior should plan the full change set and assess if an API
    contract decision is needed (escalate to Lead if so).
  repo: niall/payments-service
  branch: feature/payment-refactor
  commit: HEAD
  files:
    - src/payment/processor.py
    - src/checkout/domain.py
  line_refs:
    - "src/payment/processor.py:45-67"
    - "src/checkout/domain.py:12-30"

requirements:
  - Determine if PaymentRef type belongs in checkout/ or payment/
  - Define the processor.create_payment(checkout_id) API contract
  - Implement or produce implementation DELEGATEs

acceptance_criteria:
  - "AC1: PaymentRef type ownership is decided and documented"
  - "AC2: processor.create_payment accepts checkout_id correctly"
  - "AC3: make test passes with no failures"

escalation_triggers:
  - "Cross-service API contract decision needed → Lead Engineer"
  - "Debugging root cause spans > 2 services → Principal Engineer"
  - "Auth or security implications discovered → Security Engineer"

repro: "make test FILTER=test_payment"

skill_refs:
  - src/skills/roles/senior-engineer.md

token_budget: 8000
estimated_cost: 0.09
```

**Step 3: Senior hits arch escalation trigger → escalates to Lead**

Senior reads related files, determines the PaymentRef type crosses a domain boundary that
requires an explicit API contract decision, and emits a HANDBACK with `status: ESCALATE`
targeting Lead Engineer — including its analysis as `findings_so_far`.

**Step 4: Lead makes the decision, produces implementation DELEGATEs**

Lead Engineer emits an architecture decision document and two DELEGATE blocks:
one targeting Senior to implement the `PaymentRef` type, one targeting Engineer for
the updated `processor.py` call site.

---

### Example 3 — Security Audit (Security Engineer)

```yaml
# ~/.copilot/queue/incoming/TASK-303.yaml
---
task_id: TASK-303
type: DELEGATE
role: security-engineer
model: claude-opus-4-7
effort: max
priority: high

context:
  description: |
    Audit the JWT refresh token flow for vulnerabilities before shipping.
    Introducing sliding-window refresh: access tokens are transparently reissued
    within a 15-minute window. Concerned about replay attacks, missing expiry
    checks, and insecure token storage patterns.
  repo: niall/auth-service
  branch: feature/jwt-refresh
  commit: HEAD
  files:
    - src/auth/middleware.py
    - src/auth/tokens.py
    - src/auth/handlers.py
  line_refs:
    - "src/auth/middleware.py:45-89"
    - "src/auth/tokens.py:10-60"
    - "src/auth/handlers.py:120-175"

requirements:
  - Identify any token replay vulnerabilities
  - Check expiry validation is enforced at all code paths
  - Review token storage patterns for secrets exposure

acceptance_criteria:
  - "AC1: Findings table produced (severity, file:line, description, recommendation)"
  - "AC2: DELEGATE blocks produced for each finding"
  - "AC3: No critical findings left without an implementation path"

escalation_triggers:
  - "Compliance sign-off required beyond agent authority → surface to user"

repro: "make test FILTER=test_auth_jwt"

skill_refs:
  - src/skills/roles/security-engineer.md
  - src/skills/security/

token_budget: 12000
estimated_cost: 0.15
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

MODEL_USED: claude-opus-4-7
```

---

### Example 4 — Post-Implementation Validation (Quality Engineer)

```yaml
# ~/.copilot/queue/incoming/TASK-404-qe.yaml
---
task_id: TASK-404-qe
type: DELEGATE
role: quality-engineer
model: claude-sonnet-4-6
effort: medium
priority: normal

context:
  description: |
    Validate TASK-404 HANDBACK from Senior Engineer. Senior refactored the
    address validation module (3 files, 87 lines changed). Verify all
    acceptance criteria are met, run the test suite, assess model suitability.
  repo: niall/validation-service
  branch: feature/address-refactor
  commit: HEAD
  files:
    - src/validation/address.py
    - src/validation/postal.py
    - tests/test_address.py

requirements:
  - Verify each acceptance criterion from TASK-404
  - Run make lint && make test && make build
  - Assess whether claude-sonnet-4-6 was appropriate or if claude-haiku-4-5 would have sufficed

acceptance_criteria:
  - "AC1: make lint passes with no errors"
  - "AC2: make test passes, all address tests green"
  - "AC3: make build succeeds"
  - "AC4: quality_score populated in HANDBACK metrics"

escalation_triggers:
  - "Persistent build failures after 2 re-run attempts → Lead Engineer"
  - "Security-related failure patterns → Security Engineer"

repro: "CONFIG=dev make lint && CONFIG=dev make test && CONFIG=dev make build"

skill_refs:
  - src/skills/roles/quality-engineer.md

token_budget: 4000
estimated_cost: 0.09
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
- **Model Engineer feedback loop** — use efficiency_ratio trends to downgrade over-provisioned roles

> For full cost tracking spec, see [`src/TOKEN_METRICS.md`](TOKEN_METRICS.md).
