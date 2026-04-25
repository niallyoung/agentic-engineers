# Handoff Markup Protocol

Machine-readable format for Agent-to-Agent handoffs. Eliminates context re-duplication and enables structured task tracking.

Two block types: `DELEGATE` (sender → receiver) and `HANDBACK` (receiver → sender).

---

## DELEGATE Block Format

Used by the delegating agent (typically Orchestrator) to pass work to a specialist with complete context pre-computed.

```yaml
---
handoff_type: DELEGATE
task_id: YYYY-MM-DD-slug (e.g. 2026-04-24-fix-auth-timeout)
role: Engineer | Senior Engineer | Lead Engineer | Principal Engineer | Security Engineer
model: claude-haiku-4-5 | claude-sonnet-4-6 | claude-sonnet-4-7 | claude-opus-4-6 | claude-opus-4-7
effort: low | medium | high | max
scope: >
  One sentence: what is in scope, explicitly what is out of scope.
  Example: "Fix expired token handling in {service-name} login flow only; do not change Cognito config or other services."
context:
  - File: lambda/api/main.go:45-120 (extractAndValidateScopes function)
  - Error: "Token validation fails after 1hr on mobile; works on desktop"
  - Attempted: Added cache.Invalidate() at line 115 → no change
  - Repo state: Clean, main branch, no uncommitted files
  - Related: {service-name}/CLAUDE.md sections on JWT handling
success_criteria:
  - "make verify" passes in {service-name}
  - New test covers token refresh + 1hr expiry edge case
  - Mobile auth in e2e tests passes (npm run e2e:smoke)
  - No other repos modified
plan:
  1. Read the failing test in lambda/api/main_test.go to understand expected behavior
  2. Trace token extraction at line 45 — identify where expiry is checked
  3. Write a failing test for the 1hr edge case
  4. Fix the bug (likely in extractAndValidateScopes cache logic)
  5. Run "make verify" to confirm all tests pass
  6. Verify mobile e2e test passes
---
```

**Mandatory fields:**
- `handoff_type: DELEGATE` (literal string)
- `task_id` — unique identifier; format: `YYYY-MM-DD-<kebab-slug>` (e.g. `2026-04-24-fix-auth-timeout`). Used to link DELEGATE to HANDBACK.
- `role` — target role name (must match AGENTS.md Role column exactly)
- `model` — exact Claude model string (must match AGENTS.md Model column exactly)
- `effort` — must match AGENTS.md Effort column exactly
- `scope` — one sentence: in scope + explicitly what is out of scope
- `context` — bullet list only; no prose. Each bullet is one of: File (with line ranges), Error (from logs/stack trace), Attempted (what the delegator tried and why it failed), Repo state (uncommitted changes? branch?), Related (pointers to relevant docs)
- `success_criteria` — bullet list of observable outcomes that constitute "done"
- `plan` — numbered steps. Each step is concrete and specific (e.g. "Fix the bug at line 120" not "improve the code")

**Optional fields:** none. Keep DELEGATE minimal.

**Validation rule:** A DELEGATE block is complete if the receiving agent can execute the `plan` steps without reading any document other than the code itself (and standard language docs/package docs). If the receiving agent asks "what do I do?", the DELEGATE was incomplete.

---

## HANDBACK Block Format

Used by the receiving agent to return work to the delegator with outcome metadata.

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-fix-auth-timeout (must match the DELEGATE task_id)
status: complete | blocked | partial
deliverables:
  - Modified: lambda/api/main.go (lines 45-120)
  - Added: lambda/api/main_test.go (new test TestTokenRefreshEdgeCase_1hrExpiry)
  - Commit: abc1234 (optional; if pushed)
tests:
  - Command: "make verify" in {service-name}
  - Result: PASS (all 47 tests passed)
  - Coverage: 89% (up from 87%)
  - Mobile e2e: "npm run e2e:smoke" PASS (3/3 scenarios)
tokens_in: 1200 (approximate, from context used)
tokens_out: 820 (approximate, from response length)
model: claude-haiku-4-5 (actual model used — may differ from DELEGATE if escalated)
effort: high (actual effort used)
duration_minutes: 18
escalations: 0 (count of times escalated to different role/model)
blockers: (omitted if status is "complete" or "partial"; required if status is "blocked")
notes: "Token expiry was tracked client-side, not server-side; fixed by syncing server clock with client during refresh token exchange."
---
```

**Mandatory fields:**
- `handoff_type: HANDBACK` (literal string)
- `task_id` — must match the corresponding DELEGATE task_id exactly
- `status` — one of: `complete` (all success_criteria met), `partial` (some met, some deferred), `blocked` (cannot proceed without external decision)
- `deliverables` — bullet list of changed files and optional commit SHA
- `tests` — bullet list of test commands run and their pass/fail status
- `tokens_in` — estimate of tokens consumed reading context (DELEGATE + any necessary code reads)
- `tokens_out` — estimate of tokens produced in the response
- `model` — actual Claude model string used (may differ from DELEGATE if escalated)
- `effort` — actual effort level used
- `duration_minutes` — wall-clock time from start of task to completion
- `escalations` — count of times re-delegated to a different role/model due to complexity

**Conditional fields:**
- `blockers` — required if `status: blocked`; omitted otherwise. Bullet list of specific blockers (e.g. "requires decision on whether to break API contract", "waiting for {service-name} deployment", "type error in line 120 cannot be resolved without changing exported interface")
- `notes` — optional; any additional context for the delegator (root cause explanation, design decision made, etc.)

**Quality Engineer Feedback** (added by Quality Engineer during Tier 1/2/3 verification):
- `qe_feedback` — structured feedback for Model Engineer analysis
  - `model_assessment` — was assigned model appropriate? ("haiku_suitable", "sonnet_suitable", "sonnet_would_be_better", "opus_required")
  - `reasoning` — one sentence why model was/wasn't appropriate
  - `confidence_for_similar_tasks` — 0.0-1.0, confidence in this model for future similar tasks
  - `quality_dimensions` — optional observations on test coverage, error handling, code clarity, etc.

Example:
```yaml
qe_feedback:
  model_assessment: "haiku_suitable"
  reasoning: "Task was straightforward, well-scoped, patterns applied correctly. Haiku handled efficiently."
  confidence_for_similar_tasks: 0.92
  quality_dimensions:
    test_coverage: 87
    error_handling: "defensive"
    pattern_adherence: "excellent"
```

**Validation rule:** A HANDBACK block is complete if the delegator can determine in 30 seconds whether to accept (move to next task) or request changes (send a follow-up DELEGATE). If the delegator must re-read the code to judge quality, the HANDBACK was incomplete. QE feedback enables Model Engineer to analyze patterns and improve future routing.

---

## Usage in Agent Conversations

### When to emit DELEGATE

The delegating agent (typically Orchestrator routing to an Engineer or higher role) emits a DELEGATE block when:
1. Work is well-scoped and can be described in <200 tokens
2. A concrete `plan` has been pre-written (not "please figure out the best approach")
3. `success_criteria` are testable and observable
4. The delegator believes the target role can complete it without further clarification

Place the DELEGATE block as a fenced code block in your response, with explicit instruction: "Receive this task via DELEGATE block below; implement per the plan."

### When to emit HANDBACK

The receiving agent emits a HANDBACK block as the final output of the task, regardless of status. Place it as a fenced code block and follow it with a brief summary (no more than 2 sentences).

Example:
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-fix-auth-timeout
status: complete
...
---
```

"Task complete. Token expiry now synced server-side. All tests pass; e2e smoke tests passing. Ready for next task."

---

## Example: Bug Triage Workflow

### Orchestrator → Lead Engineer (diagnosis)

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-bug-expired-tokens-mobile
role: Lead Engineer
model: claude-sonnet-4-7
effort: high
scope: Diagnose why token validation fails after 1hr on mobile but not desktop. Do not fix yet; just root-cause analysis.
context:
  - File: lambda/api/main.go:45-120 (extractAndValidateScopes)
  - Error: "Unauthorized: token expired" on iOS app after 1hr; desktop (Chrome) works fine
  - Logs: {service-name} logs show "token claims invalid at 3600s"
  - Attempted: Team tried cache invalidation → no change
  - Repo: Clean, main branch
plan:
  1. Read {service-name} CLAUDE.md to understand token lifecycle
  2. Examine extractAndValidateScopes at line 45 — trace the expiry check
  3. Compare with {service-name} token refresh logic (src/services/auth.ts)
  4. Check if client-side clock sync is the issue (clock skew between mobile and server)
  5. Write a diagnosis note with hypothesis and evidence
success_criteria:
  - Root cause identified with specific file:line evidence
  - One paragraph explaining the bug mechanism
  - Recommended fix strategy (no implementation yet)
---
```

### Lead Engineer → Orchestrator (diagnosis complete)

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-bug-expired-tokens-mobile
status: complete
deliverables:
  - Analysis: Root cause is client-side clock skew on mobile. Server checks expiry against server time (UTC); mobile client uses device clock (which may lag 10-60s). At exactly 1hr boundary, mobile clock is behind, token appears unexpired on client but expired on server.
  - Evidence: lambda/api/main.go:92 checks `time.Now()` against claim `exp`. Mobile device clocks not synced with NTP pool.
  - Fix strategy: Add 30s grace period in extractAndValidateScopes OR sync client clock via headers during token refresh.
tests:
  - No code changes; analysis only
tokens_in: 1400
tokens_out: 950
model: claude-sonnet-4-7
effort: high
duration_minutes: 22
escalations: 0
notes: "The bug is genuine but subtle — only manifests on devices with clock skew. The 30s grace period approach is lower-risk than forcing NTP sync."
---
```

### Orchestrator → Engineer (implementation)

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-fix-token-grace-period
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Implement 30s token expiry grace period in {service-name}. Do not change authentication flow or Cognito config.
context:
  - File: lambda/api/main.go:92 (expiry check in extractAndValidateScopes)
  - Root cause analysis from Lead Engineer (preceding HANDBACK block)
  - Design decision: Add 30s grace window to exp claim validation
  - Related: {service-name}/CLAUDE.md sections on token lifecycle
plan:
  1. Write a failing test: TestTokenExpiryGracePeriod that verifies a token 25s expired is still accepted
  2. Modify line 92 in lambda/api/main.go: change `time.Now()` to `time.Now().Add(-30 * time.Second)`
  3. Run "make verify" — test should now pass
  4. Verify no other tests broke
  5. Commit with message: "fix(identity): add 30s grace period for token expiry to handle clock skew"
success_criteria:
  - "make verify" passes (all tests pass)
  - New test TestTokenExpiryGracePeriod added and passing
  - Mobile e2e auth tests pass
  - No other repos modified
---
```

---

## Quality Engineer Verification & Feedback Loop

After Engineer/Senior Engineer returns HANDBACK, Quality Engineer verifies task quality and provides feedback for optimization.

**QE Verification Process:**
1. Run Tier 1 checklist (lint, tests, coverage, production hazards)
2. If Tier 1 PASS: Complete verification and add `qe_feedback` block to HANDBACK
3. If Tier 1 FAIL: Return to Engineer for rework (new DELEGATE with status `rework`)

**QE Feedback Structure (added to HANDBACK):**

```yaml
qe_feedback:
  tier_1_verdict: PASS | FAIL
  model_assessment: "haiku_suitable" | "sonnet_suitable" | "sonnet_would_be_better" | "opus_required"
  reasoning: "Brief explanation of model suitability for this task"
  confidence_for_similar_tasks: 0.85
  quality_dimensions:
    test_coverage: 87
    error_handling: "defensive"
    code_clarity: "clear"
    pattern_adherence: "follows conventions"
  notes: "Any additional observations for Model Engineer"
```

**Model Engineer Uses This Feedback To:**
- Analyze whether assigned model was optimal for task type/complexity
- Build confidence scores for future task routing
- Identify task types where model selection could improve
- Recommend model/effort changes for similar future tasks

This creates a feedback loop: Engineer → QE → Model Engineer → improved routing for next similar task.

---

## Automatic Usage Tracking Integration

The `skills/usage-tracking/` skill is automatically invoked at key workflow points to monitor token consumption and enable budget-aware decisions.

### Automatic Invocation Points

**1. Session Start (Orchestrator)**
```bash
# Initialize tracking at session start
bash skills/usage-tracking/scripts/capture_token_usage.sh
# Output: Baseline usage captured, shows current status
```
→ Establishes starting point for session analysis

**2. Before Major DELEGATE (Orchestrator)**
```bash
# Before delegating work to Engineer/Senior/etc.
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
# Check session.current — if >85%, switch to Haiku or defer
```
→ Decision: GREEN (proceed normally) / YELLOW (use Sonnet, estimate tokens) / RED (Haiku only or defer)

**3. At 30-Minute Checkpoints (Orchestrator)**
```bash
# Periodic status check during active session
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
# Output shows: current%, velocity, hours to reset, trend
```
→ Decision: Continue normally, adjust model tier, or break until reset

**4. In HANDBACK Block (All Agents)**

Agents automatically include usage metrics in HANDBACK:

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-25-example-task
status: complete
...
metrics:
  usage_before_session_pct: 65
  usage_after_session_pct: 71
  tokens_consumed_estimate: 2100
  session_velocity_pct_per_hour: 2.4
  model_used: claude-sonnet-4-6
  efficiency_note: "Token consumption 8% below baseline for similar scope"
---
```

→ Feeds into daily analysis; Model Engineer uses to improve routing

**5. Session End (Orchestrator)**
```bash
# Final status capture
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
# Output: Complete session metrics, velocities, reset forecast
```
→ Recorded for historical analysis and trend detection

### Workflow with Automatic Tracking

```
SESSION START:
├─ Orchestrator: capture_token_usage.sh
│  └─ Output: "Session 0%, Weekly 35%, GREEN status"
│
EVERY 30 MINUTES:
├─ Orchestrator: snapshot (automatic at checkpoints)
│  └─ Output: "Session 42%, trend rising 5%/hr, 11.6 hours to reset"
│  └─ Decision: GREEN → continue, delegate to Engineer with Sonnet
│
BEFORE DELEGATION:
├─ Orchestrator: analyze --json
│  └─ Check session.current in JSON
│  └─ Route to appropriate model based on budget
│
DURING ENGINEER WORK:
├─ Engineer: Silent capture (if tracking budget internally)
│  └─ bash capture_token_usage.sh --silent
│
IN HANDBACK RESPONSE:
├─ Engineer: Include metrics section
│  └─ usage_before, usage_after, tokens_consumed
│  └─ Model used, efficiency notes
│
AT NEXT CHECKPOINT:
├─ Orchestrator: snapshot again
│  └─ Verify consumption was as expected
│  └─ Adjust for next delegation
│
SESSION END:
└─ Orchestrator: analyze + final metrics
   └─ Record in daily summary for Model Engineer
```

### Integration with Budget-Aware Delegation

DELEGATE block includes automatic budget assessment:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-refactor-auth-handler
role: Engineer
model: claude-sonnet-4-6
effort: medium
budget_context:
  session_pct_at_delegation: 65
  estimated_tokens_needed: 2500
  hours_until_reset: 4.2
  status: YELLOW
  recommendation: "Sonnet sufficient; estimate tokens to stay under 72%"
...
---
```

→ Engineer sees budget context upfront, can optimize token usage

### Data Feeding Into Daily Analysis

Each HANDBACK's metrics:
1. Gets recorded with timestamp
2. Aggregated by Model Engineer in daily analysis
3. Used to identify patterns: which task types consume most tokens, which models are optimal, when to escalate
4. Feeds back into improved routing for tomorrow's tasks

### Automatic Alerts

Voice alerts trigger automatically when thresholds hit:
```bash
# 70% session warning (Daniel voice)
"Session usage high, 70 percent"

# 85% session critical (Daniel voice)  
"Session usage critical, 85 percent"
```

→ No explicit agent action needed; alerts inform decisions naturally

---

## Testing the Protocol (TDD verification)

To validate this protocol spec, apply it to three real workflows from ORCHESTRATION.md:

1. **Security Audit Workflow** — Orchestrator → Guardian (security analysis) → Orchestrator → Engineer (fix)
2. **Bug Triage Workflow** — Orchestrator → Lead Engineer (diagnosis) → Orchestrator → Engineer (fix)
3. **Feature Implementation** — Orchestrator → Principal Engineer (plan) → Orchestrator → Senior Engineer (impl)

For each workflow, write the DELEGATE and HANDBACK blocks that would be exchanged. The protocol is correct if:
- No cross-document references are needed (DELEGATE is self-contained)
- The receiving agent can execute blindly per the plan without ambiguity
- The HANDBACK provides enough detail for the delegator to verify success in 30 seconds
- All three workflows use the same DELEGATE/HANDBACK format with no special cases

---

## When to NOT Use DELEGATE/HANDBACK

- Orchestrator solo work (routing, status checks) — no DELEGATE needed
- One-off questions or clarifications — use natural language
- Internal reasoning within a single agent response — no markup needed

DELEGATE/HANDBACK is for work handoff between agents.
