# Agent Skills & Workflows

Role-specific execution details. Complements AGENTS.md (who, when, routing) and QUEUE-PROTOCOL.md (mechanics).

> **Current skill roster:** See [`src/SKILLS.md`](../src/SKILLS.md) for the canonical, current list of the 8 surviving skills post-2026-08-11 slimdown (orchestrator, queue-management, queue-query, protocol-validator, spec-validator, spec-management, skill-improvement-feedback, codex-agent-cleanup).

---

## Validation & Error Handling Patterns

All agent implementations MUST follow these validation and error handling patterns:

### Input Validation
1. **DELEGATE Block Validation:**
   - Check all mandatory fields present: task_id, role, scope, success_criteria
   - Validate task_id format matches queue naming conventions
   - Ensure role matches agent's authorized role
   - Verify plan exists (except for Senior Engineer planning tasks)
   - Reject task with `status: blocked` if critical fields missing

2. **Scope & Plan Validation:**
   - Confirm scope is achievable within effort level and time constraints
   - Verify plan aligns with scope and success criteria
   - Flag any scope creep or contradictions immediately
   - Request clarification before proceeding if ambiguous

### Error Handling
1. **Recoverable Errors** (request clarification, retry):
   - Missing or unclear success criteria → Request DELEGATE modification
   - Conflicting plan steps → Request clarification in HANDBACK comment
   - Dependency not met → Report `status: blocked` with reason
   
2. **Critical Errors** (escalate to Lead Engineer):
   - Architectural conflicts discovered during execution
   - Security concerns or policy violations
   - Resource limits exceeded (time, tokens, disk space)
   - Third-party service failures (if any external calls attempted)

3. **HANDBACK Error Format:**
   ```yaml
   status: blocked | error
   decision: ESCALATE
   severity: low | medium | high | critical
   error_message: "Clear description of what went wrong"
   remediation: "Suggested next steps for resolution"
   ```

### Quality Validation
1. **Code Quality Checklist:**
   - Run linters specified in repo (before committing)
   - Verify all tests pass (new + existing)
   - Confirm no sensitive data in logs or deliverables
   - Check documentation updated if applicable

2. **Deliverable Validation:**
   - All changes committed with descriptive messages
   - No temporary files or debug code left behind
   - Success criteria objectively verified
   - Token usage and metrics captured for Model Engineer feedback

---

## Engineer

**Model:** claude-haiku-4.5 (high effort)  
**Cost Target:** 18%

Execute well-scoped tasks with pre-written plans. Recommended (not mandatory): use Red-Green TDD when writing code (test first, implement, refactor).

**Workflow:**
1. Read DELEGATE carefully
2. Follow plan steps in order
3. Run `make verify` before HANDBACK
4. Document deliverables and test results clearly

**Escalation trigger:** Report `status: blocked` if you hit architectural conflicts or missing context.

---

## Senior Engineer

**Model:** claude-sonnet-5 (high effort)  
**Cost Target:** 7%

Design solutions for complex tasks without pre-written plans. Diagnose bugs when root cause is unclear.

**Planning task:** Explore 2-3 approaches, write detailed plan with rationale, return HANDBACK with plan (not code).

**Diagnosis task:** Reproduce issue, trace code flow, point to specific file:line, explain root cause with evidence, suggest fixes.

**Escalation trigger:** Cross-service changes, architectural impacts, security concerns → report `status: blocked`.

---

## Lead Engineer

**Model:** claude-sonnet-5 (high effort)  
**Cost Target:** 2%

Review code and unblock stuck tasks. Verify quality before work proceeds.

**Code review checklist:**
- Tests pass, lint clean, coverage maintained
- No secrets, panics, or scope creep
- For Senior Engineer code: coverage ≥85%, plan completeness verified
- For Principal Engineer code: architecture patterns followed, IAM correct

**Verdict:** PASS or FAIL (with specific feedback if FAIL).

**Unblock task:** Analyze blocker, provide path forward, return to Orchestrator.

---

## Quality Engineer

**Model:** claude-sonnet-5 (medium effort)  
**Cost Target:** 8%

Run Tier 1 quality checks. Assess model performance.

**Checks:** Same as Lead Engineer (tests, lint, no secrets, scope match).

**Model assessment:** Was this model appropriate? (haiku_suitable / sonnet_would_be_better / opus_required). Confidence score (0.0–1.0).

**Feedback:** Add to HANDBACK for Model Engineer analysis.

---

## Principal Engineer

**Model:** claude-opus-5 (high effort)  
**Cost Target:** 1%

Design when changes affect >2 repos or touch service boundaries.

**Task:** Map dependencies, identify contracts, design approach (breaking vs. compatibility vs. versioning), propose rollout plan.

---

## Security Engineer

**Model:** claude-fable-5 (max effort, defensive-only)  
**Cost Target:** 1%

Scan for vulnerabilities, check dependencies, verify access controls, return findings by severity (CRITICAL, HIGH, MEDIUM, LOW).

---

## Model Engineer

**Model:** claude-sonnet-5 (high effort)  
**Cost Target:** 3%

**Primary:** Analyze completed task feedback (~10-100 samples). Identify patterns: which models succeed? Which fail? Token efficiency?

**Output:** Ranking for next similar task (Rank 1 = highest confidence, Rank 2 = exploratory, Rank 3 = fallback).

Orchestrator uses Rank 1 for the next matching task.

**Secondary (Audit Trail):** Generate `artifacts/index.json` periodically
- Scan artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN files
- Extract metadata: task_id, agent_type, status, tokens, cost, severity, decision
- Create searchable index by: file_type, task_id, agent_type, status
- Include stats: total_tokens, total_cost, critical_issues, escalations
- Store as: artifacts/index.json (human-readable, version-controlled in artifacts/)

**Skill:** Artifact indexing as part of feedback loop analysis (cost tracking enables Model Engineer's recommendations).

---

## Orchestrator

**Model:** claude-haiku-4.5 (low effort)  
**Cost Target:** 60%

Central coordinator for agent-based task routing and queue management. Runs continuously in harness, polling queues every 30-60 seconds. No external tools or cron jobs — 100% agent-based delegation.

---

### SKILL: Queue Polling

**Trigger:** Every 30-60 seconds, scan for new work in three queue directories.

**What to do:**

1. **Poll `artifacts/queue/incoming/`** for new tasks (YAML files matching pattern `{task_id}.yaml`)
   - Read task metadata: task_id, description, priority
   - Check for prerequisites/blockers (e.g., waiting on other task)
   - If blocked → move to "waiting" state (or hold); if ready → proceed to routing

2. **Poll `artifacts/queue/processing/`** for agent completions (HANDBACK files matching pattern `{task_id}-HANDBACK-{role}.yaml`)
   - Read HANDBACK status, deliverables, tokens, test results
   - Validate HANDBACK format (see HANDOFF.md)
   - Route to Quality Engineer if complete; escalate to Lead/Senior Engineer if blocked

3. **Poll `artifacts/queue/done/`** for human-reviewed decisions (decision files matching pattern `{task_id}-{decision}.yaml`)
   - Check decision: PROCEED (merge), REWORK (return to incoming with feedback), ESCALATE (promote role)
   - Act on decision (move artifact to archive, create rework DELEGATE, etc.)

**Success Criteria:**
- All three queues polled within poll cycle
- No tasks missed or left hanging in processing
- HANDBACK validation catches malformed responses (agents report incomplete work early)
- Tasks transition cleanly: incoming → processing → done → archive

**Error Handling:**
- Malformed YAML → skip, log error, alert human to fix
- HANDBACK missing mandatory fields → reject, return to agent with correction request
- Stuck task (in processing >2 hours without activity) → escalate to Lead Engineer for investigation

---

### SKILL: DELEGATE Validation & Creation

**Trigger:** When task arrives in `incoming/` queue and routing decision is made.

**What to do:**

1. **Validate incoming task format**
   - Confirm task_id follows format: `YYYY-MM-DD-{kebab-slug}` (e.g. `2026-05-02-fix-auth-timeout`)
   - Check required fields: description, priority
   - Check for duplicate task_id (if exists, skip and alert)

2. **Apply AGENTS.md routing decision tree** to determine target role:
   - Is task security-scoped (auth, crypto, vulnerabilities)? → **Security Engineer**
   - Else if task requires cross-service architecture (affects >2 repos)? → **Principal Engineer**
   - Else if task is complex coding WITHOUT pre-written plan? → **Senior Engineer** (to write plan first)
   - Else if task is code review or quality gate? → **Lead Engineer** or **Quality Engineer**
   - Else if task is well-planned, low-medium complexity? → **Engineer**
   - Else → Escalate to human (unclear scope, halt progress)

3. **Create DELEGATE block** with mandatory fields:
   - `handoff_type: DELEGATE` (literal)
   - `task_id` (from incoming task)
   - `role` (from routing decision, must match AGENTS.md exactly)
   - `model` (from AGENTS.md role row, or apply Model Engineer recommendation if available)
   - `effort` (from AGENTS.md role row)
   - `scope` (one sentence: in scope + explicitly out of scope)
   - `context` (bullet list: file references, error logs, root cause, attempted solutions, repo state)
   - `plan` (numbered concrete steps; required for Engineer and Senior Engineer)
   - `success_criteria` (bullet list of observable outcomes = "done")

4. **Store DELEGATE** in `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`
   - Use date from task_id for directory (e.g., YYYY-MM-DD from task_id 2026-05-02-...)

5. **Move task** from `incoming/` to `processing/` state
   - File stays in artifacts/queue/processing/ awaiting HANDBACK

**Success Criteria:**
- DELEGATE is complete and unambiguous (receiving agent needs NO clarification)
- All mandatory fields present
- DELEGATE passes validation (format check in HANDOFF.md)
- Plan steps are concrete (e.g., "Fix line 92 in main.go" not "improve the code")
- scope clearly separates in-scope from out-of-scope work

**Error Handling:**
- Routing decision tree returns "escalate to human" → hold task, alert human
- Mandatory DELEGATE field missing → create checklist for human to fill in
- Plan too vague or underspecified → return to human for clarification (don't delegate incomplete work)

---

### SKILL: Routing Decision Tree Application

**Trigger:** Part of DELEGATE creation; applied once per task.

**What to do:**

Apply the routing decision tree in order, stopping at first match:

1. **Security-scoped check:**
   - Scan task description/scope for keywords: auth, crypto, secret, key, token, vulnerability, access control, permission, vulnerability
   - If yes → **Security Engineer** (Opus model, max effort)
   - Confidence: Treat as high-confidence decision (security always escalates)

2. **Cross-service check:**
   - Scan scope/context for repo references: affects >2 distinct repos?
   - If yes → **Principal Engineer** (Opus model, high effort)
   - Confidence: High

3. **Complex coding without plan:**
   - Is task description a coding task (modify, implement, debug)?
   - AND does incoming task lack pre-written plan (plan field empty/missing)?
   - If yes → **Senior Engineer** (Sonnet model, high effort, role: plan writer)
   - Set DELEGATE role to "Senior Engineer" with task: "Write plan for [description]"
   - Senior Engineer returns plan; Orchestrator creates second DELEGATE for Engineer

4. **Code review or quality gate:**
   - Is task explicitly "review", "verify", "audit", "quality check"?
   - If yes → check if post-implementation: **Quality Engineer** (Sonnet model, medium effort)
   - If pre-decision guidance needed: **Lead Engineer** (Sonnet model, high effort)

5. **Well-planned, low-medium complexity:**
   - Is task description simple (few files, clear steps)?
   - AND does incoming task include plan?
   - If yes → **Engineer** (Haiku model, high effort)

6. **Default escalation:**
   - Scope is unclear, too large, or spans multiple specialties
   - Return to human: "Cannot route; clarify scope or break into smaller tasks"

**Success Criteria:**
- Routing decision is deterministic (same task description → same routing every time)
- Confidence score ≥0.85 for security, cross-service, code review; ≥0.70 for others
- Agent role and model match AGENTS.md exactly
- Escalations to human are brief and actionable

**Error Handling:**
- Ambiguous task → escalate to human with clarification questions
- Task matches multiple routes → apply priority (security > cross-service > complex > review > simple)
- Model Engineer recommendation conflicts with routing → apply recommendation if confidence ≥0.80, else use AGENTS.md default

---

### SKILL: Agent Delegation (DELEGATE Transmission)

**Trigger:** After DELEGATE creation and storage.

**What to do:**

1. **Invoke appropriate agent** with DELEGATE as context
   - Method: Pass DELEGATE block (YAML) as input to agent
   - Include agent role, model, effort level in invocation
   - Do NOT expect immediate response (agents run asynchronously)

2. **Log invocation** with metadata:
   - task_id, role, model, effort
   - timestamp (start_time)
   - DELEGATE file path for reference

3. **Mark task** `processing/` state
   - Task is now awaiting HANDBACK from agent
   - Orchestrator continues polling other queues

**Success Criteria:**
- Agent receives DELEGATE without truncation or format corruption
- Orchestrator can correlate invocation to incoming task_id
- Task is tracked in processing state (won't be re-delegated)

**Error Handling:**
- Agent invocation fails (timeout, harness error) → log error, retry up to 3 times with exponential backoff (1s, 2s, 4s)
- After 3 retries → escalate to human: "Agent invocation failed; manual intervention needed"

---

### SKILL: HANDBACK Reception & Validation

**Trigger:** When agent returns HANDBACK file in `artifacts/queue/processing/`.

**What to do:**

1. **Poll for HANDBACK** (every 30-60s with incoming and done queues)
   - Check file naming: `{task_id}-HANDBACK-{role}.yaml`
   - Match task_id to original incoming task

2. **Read and validate HANDBACK** format:
   - Mandatory fields (see HANDOFF.md): handoff_type, task_id, status, deliverables, tests, tokens_in, tokens_out, model, effort, duration_minutes
   - Check status value: `complete | blocked | partial` (reject other values)
   - Validate task_id matches DELEGATE exactly
   - Parse tokens_in/tokens_out as integers; reject invalid values

3. **Extract metadata for routing:**
   - Extract: agent_role, status, deliverables, test_results, tokens_in, tokens_out, model
   - If status == `complete` → route to Quality Engineer
   - If status == `blocked` → escalate to Lead Engineer or Senior Engineer (depending on complexity)
   - If status == `partial` → review and either return to agent with feedback or escalate

4. **Store HANDBACK** in processing queue for next stage processing
   - File already written by agent; Orchestrator just reads and routes

**Success Criteria:**
- HANDBACK validation catches format errors (incomplete, wrong field types)
- task_id validation prevents cross-task contamination (e.g., HANDBACK matched to wrong DELEGATE)
- Status routing is deterministic (same status → same next stage)
- Test results are readable and actionable (agent clearly states pass/fail)

**Error Handling:**
- Malformed HANDBACK (missing mandatory fields) → return to agent with checklist of missing fields; agent resubmits
- status == `blocked` but no blocker reason provided → ask agent to clarify, then escalate
- tokens_in/tokens_out missing or invalid → use estimate from agent's note, or escalate to Model Engineer

---

### SKILL: HANDBACK Routing (Processing → QE or Escalation)

**Trigger:** After HANDBACK validation, based on status.

**What to do:**

**Case 1: status == `complete`**
1. Route to Quality Engineer
2. Create routing metadata: task_id, agent_role, deliverables summary, test_results, tokens
3. Quality Engineer reviews for: test pass, lint clean, no secrets, coverage maintained, spec compliance
4. QE returns Pass (→ done/PROCEED) or Fail (→ rework/REWORK)

**Case 2: status == `blocked`**
1. Read blocker reason from HANDBACK
2. Route to appropriate unblock agent:
   - If architectural/design blocker → Senior Engineer (high effort, role: unblock/advise)
   - If quality/validation blocker → Lead Engineer (high effort, role: review/advise)
   - If missing context/clarification → Lead Engineer (high effort)
3. Unblock agent reviews blocker, provides guidance or revised plan
4. Orchestrator creates new DELEGATE with guidance and returns to `incoming/` for retry

**Case 3: status == `partial`**
1. Review deliverables: what was completed, what was deferred?
2. Route to Quality Engineer for partial review
3. QE may approve (with deferred work tracked separately) or request completion
4. If approved → move to done/PROCEED (with deferred work as separate task)
5. If denied → return to incoming/REWORK with feedback

**Success Criteria:**
- Routing is deterministic (same status/blocker → same next stage)
- Quality Engineer receives only complete work (status == `complete`)
- Escalations to Senior/Lead Engineer include clear blocker reason
- Partial work is tracked separately (deferred items become new incoming tasks)

**Error Handling:**
- Blocker reason is unclear → escalate to human with blocker and HANDBACK for review
- Status is ambiguous (e.g., `completed` instead of `complete`) → reject, ask agent to use canonical value
- Task arrives at done/PROCEED without QE review → flag as missing quality gate; require QE sign-off

---

### SKILL: Span Capture (Custom span format Observability)

**Trigger:** When Orchestrator receives and processes HANDBACK from any agent.

**What to do:**

1. **Extract span attributes from HANDBACK:**
   - task_id, agent_role, agent_model, status
   - tokens_in, tokens_out (from HANDBACK)
   - deliverables count (length of deliverables list)
   - test_results (pass/fail count, coverage if available)
   - duration_minutes (from HANDBACK)

2. **Calculate derived metrics:**
   - total_tokens = tokens_in + tokens_out
   - cost_usd = (tokens_in × model_input_price + tokens_out × model_output_price)
     - Use pricing from AGENTS.md or external pricing table (Haiku: $0.03, Sonnet: $0.09, Opus: $0.15 per task estimated)
   - decision = inferred from status and next routing (complete → QE, blocked → escalate, etc.)
   - severity = inferred from status (complete → none, partial → medium, blocked → high)

3. **Create SPAN** with custom span schema:
   - trace_id: unique identifier for this task's execution chain (reuse same trace_id if same task spawns multiple agents)
   - span_id: unique identifier for this agent's work (generated UUID or hash)
   - parent_span_id: trace_id of DELEGATE (if exists)
   - span_name: `agent.{role}.execution` (e.g., `agent.engineer.execution`)
   - start_time: from DELEGATE creation time (or best estimate)
   - end_time: current time when HANDBACK received
   - duration_ms: (end_time - start_time) in milliseconds
   - status: `success` (if status == complete), `error` (if blocked), `unknown` (if partial)
   - attributes:
     - agent_type: role name (e.g., "Engineer")
     - agent_model: model string (e.g., "claude-haiku-4.5")
     - service_name: "orchestrator-queue" (literal)
     - task_id, priority
     - input_tokens, output_tokens, total_tokens, cost_usd
     - deliverables_count, test_pass_count, test_fail_count, coverage_percent (if available)
     - decision (PROCEED, REWORK, ESCALATE, etc.)
     - severity (none, medium, high)
     - confidence (0.0-1.0; extracted from routing decision if available)

4. **Write SPAN file:**
   - Path: `artifacts/YYYY-MM-DD/SPAN-{timestamp}-{agent_role}.yaml`
   - Use date from task_id (e.g., 2026-05-02 from task_id 2026-05-02-fix-auth-timeout)
   - Use timestamp = current time (ISO 8601, seconds precision) in filename
   - Format: YAML with custom span schema (human-readable for debugging)

5. **Optional (async, low priority):** Request Model Engineer to regenerate `artifacts/index.json`
   - This enables cost tracking and trend analysis

**Success Criteria:**
- Every completed task has a corresponding structured span record file (100% capture rate)
- SPAN attributes are accurate (cost calculation verified, tokens match HANDBACK)
- SPAN files are archived and queryable (Model Engineer can read and analyze)
- No performance impact on Orchestrator (span capture is <1ms overhead)

**Error Handling:**
- Cost calculation fails (unknown model) → use estimate or mark as "unknown", don't block HANDBACK processing
- Timestamp parse error → use current time as fallback
- File I/O error writing SPAN → log error, continue (don't block task routing)

---

### SKILL: Artifact Indexing (Model Engineer Support)

**Trigger:** Periodically, as part of feedback loop analysis (Model Engineer requests this).

**What to do:**

This SKILL is **performed by Model Engineer**, not Orchestrator directly, but Orchestrator coordinates the request:

1. **Orchestrator maintains index state** (optional):
   - Track when last index generation ran
   - If Model Engineer hasn't regenerated in >24 hours, schedule regeneration

2. **Index generation workflow** (Model Engineer executes):
   - Scan `artifacts/YYYY-MM-DD/` directories for DELEGATE, HANDBACK, SPAN files
   - Extract metadata from each file:
     - task_id, agent_type, agent_model, status
     - tokens (total_tokens, cost_usd)
     - decision (PROCEED, REWORK, ESCALATE, or inferred from SPAN)
     - severity (none, medium, high, critical)
     - create_date (from file timestamp or task_id)
   - Group by: file_type (DELEGATE/HANDBACK/SPAN), task_id, agent_type, status, severity
   - Calculate stats:
     - total_tokens (sum of all spans)
     - total_cost_usd (sum of all costs)
     - escalation_count (tasks with ESCALATE decision)
     - rework_count (tasks with REWORK decision)
     - critical_issues (tasks with severity=critical)
     - average_duration_minutes, median, p95 (across all tasks)
   - Build searchable index structure (JSON):
     ```json
     {
       "generated_at": "2026-05-02T14:30:00Z",
       "summary": {
         "total_tasks": 42,
         "total_tokens": 125000,
         "total_cost_usd": 15.25,
         "escalation_count": 3,
         "rework_count": 5,
         "critical_issues": 0
       },
       "by_agent_type": {
         "Engineer": { "count": 25, "tokens": 65000, "cost": 7.50, "success_rate": 0.92 },
         "Senior Engineer": { "count": 8, "tokens": 35000, "cost": 4.20, "success_rate": 0.87 },
         ...
       },
       "by_status": {
         "complete": { "count": 37, "tokens": 110000, "cost": 13.50 },
         "blocked": { "count": 3, "tokens": 10000, "cost": 1.20 },
         "partial": { "count": 2, "tokens": 5000, "cost": 0.55 }
       },
       "files": [
         {
           "path": "artifacts/2026-05-02/DELEGATE-2026-05-02-fix-auth-timeout-Engineer.yaml",
           "type": "DELEGATE",
           "task_id": "2026-05-02-fix-auth-timeout",
           "agent_type": "Engineer",
           "status": "pending"
         },
         ...
       ]
     }
     ```

3. **Write index file:**
   - Path: `artifacts/index.json` (root of artifacts directory)
   - Format: JSON, human-readable (pretty-printed)
   - Include version/schema info for future compatibility

4. **Use for trending and recommendations:**
   - Identify cost patterns (which agent types are most expensive? which are most reliable?)
   - Recommend model downgrades (e.g., "Haiku outperforms Sonnet on simple tasks")
   - Flag escalation trends (e.g., "Senior Engineer blocked rate increased 20% this week")

**Success Criteria:**
- Index includes 100% of artifact files (no missing tasks)
- Cost calculations are accurate and match SPAN data
- Index is queryable and useful for Model Engineer analysis
- Index generation completes <1 minute (doesn't slow down feedback loop)

**Error Handling:**
- File not found (artifact deleted) → skip with warning, include in "missing" section
- Corrupted YAML → skip with error, note in index
- Date parsing error → use filename date as fallback

---

### Core Workflow Summary

Orchestrator executes this cycle every 30-60 seconds:

```
1. Poll incoming/ → for each task:
   ├─ Validate format
   ├─ Apply routing decision tree
   ├─ Create DELEGATE
   ├─ Store DELEGATE in artifacts/delegates/
   └─ Delegate to appropriate agent

2. Poll processing/ → for each HANDBACK:
   ├─ Validate format
   ├─ Extract metadata
   ├─ Capture structured span record
   └─ Route to QE or escalation path

3. Poll done/ → for each decision:
   ├─ Check decision (PROCEED/REWORK/ESCALATE)
   ├─ Act on decision
   ├─ Move to archive
   └─ Create new tasks if rework/escalation

4. Apply Model Engineer recommendations:
   ├─ Read artifacts/model-engineer-recommendations.yaml (if exists)
   ├─ Use Rank 1 model for next similar task
   └─ Clear recommendation file after use
```

Each cycle is independent; tasks progress through queues asynchronously. No blocking, no external tools, 100% agent-based.

---

## Summary

| Role | Task | Output | Next |
|------|------|--------|------|
| **Engineer** | Execute plan | Code + tests | Quality Engineer |
| **Senior Engineer** | Plan or diagnose | Plan or diagnosis | Engineer or Lead Engineer |
| **Lead Engineer** | Review/unblock | Approval or guidance | Merge or rework |
| **Quality Engineer** | Gate check | Pass/fail + feedback | Merge or rework |
| **Principal Engineer** | Design | Architecture + plan | Engineer for impl |
| **Security Engineer** | Audit | Findings TODO | Engineer for fixes |
| **Model Engineer** | Analyze feedback | Routing recommendations | Orchestrator (applies) |
| **Orchestrator** | Manage queue | Route + transition | Agents + humans |


---

### SKILL: Queue State Transitions (Task Movement)

**Trigger:** After routing decision and delegation, before agent processing; after HANDBACK received.

**What to do:**

1. **Move task from `incoming/` to `processing/`:**
   - Read task file: `~/.copilot/queue/incoming/{task_id}.yaml`
   - Create agent context with routing info (role, model, effort)
   - Move file to: `~/.copilot/queue/processing/{task_id}.yaml`
   - Success = task locked for exclusive agent processing

2. **Move task from `processing/` to `done/`:**
   - Read HANDBACK file: `~/.copilot/queue/processing/{task_id}-HANDBACK.yaml`
   - Validate HANDBACK has decision field (PROCEED / REWORK / ESCALATE)
   - Move task to: `~/.copilot/queue/done/{task_id}-{DECISION}.yaml`
   - Success = task archived; decision tracked

**Error Handling:**
- Task file not found → log error, alert human
- Concurrent access (task in both states) → revert, escalate to Lead Engineer
- HANDBACK missing/malformed → hold in processing, request correction from agent

**Success Criteria:**
- Task always in exactly one state (incoming OR processing OR done)
- No lost tasks or orphaned files
- State transitions are atomic (all-or-nothing)
- Full audit trail preserved

---

### SKILL: Agent Invocation & HANDBACK Reception

**Trigger:** After moving task to `processing/`.

**What to do:**

1. **Invoke agent for task:**
   - Read task: `~/.copilot/queue/processing/{task_id}.yaml`
   - Extract: role, model, effort, scope, plan, success_criteria
   - Invoke agent via CLI with task context (NOT direct Python import)
   - Pass context: task_id, role, model, deadline, scope
   - Set timeout based on effort (low=15min, medium=30min, high=60min, max=120min)
   - Wait for agent completion

2. **Receive HANDBACK:**
   - Agent writes: `~/.copilot/queue/processing/{task_id}-HANDBACK.yaml`
   - Read HANDBACK and validate mandatory fields:
     - handoff_type: "HANDBACK"
     - task_id, status, role, model
     - tokens_in, tokens_out, duration_minutes
     - decision: PROCEED / REWORK / ESCALATE
     - confidence (0.0–1.0)
   - Extract metadata: cost, token count, severity
   - Capture structured span record for observability
   - Route to next step based on decision

**Error Handling:**
- Agent timeout → escalate to Lead Engineer for investigation
- HANDBACK missing/malformed → request correction from agent
- Agent failure → move task back to incoming with error context
- Decision ambiguous → escalate to Lead Engineer

**Success Criteria:**
- Agent completes within timeout
- HANDBACK arrives with all mandatory fields
- SPAN captured for metrics/feedback
- Decision clearly stated and actionable

---

## doc-quality Skill

**Location:** `~/.config/opencode/skills/doc-quality/`  
**Role:** Quality Engineer  
**Trigger:** on-demand | pre-commit | ci-cd | scheduled (weekly)

Documentation quality monitoring skill for link validation, cross-reference checks, staleness flagging, and quality metrics.

### Features

1. **Link Validation** — Check all markdown links (internal + external), report broken links with line numbers
2. **Cross-Reference Validation** — Check INDEX.md coverage, detect orphaned files, circular references
3. **Staleness Detection** — Flag files not updated in 30+ days, detect TODO/FIXME comments
4. **Quality Metrics** — Heading hierarchy, code block syntax, readability
5. **Report Generation** — HTML + Markdown reports with Critical/Warning/Info priority levels

### Invocation

```bash
# Manual (full check)
python ~/.config/opencode/skills/doc-quality/scripts/validate_docs.py --docs-dir docs/ --output-format both

# CLI wrapper
opencode-doc-quality --docs-dir docs/

# Pre-commit hook (critical issues only)
bash ~/.config/opencode/skills/doc-quality/scripts/pre_commit_hook.sh
```

### Constraint

**SPEC.md is always excluded** from all checks (protected document). This is enforced independently in every validator module.

### Exit Codes

- `0` — No issues found
- `1` — Issues found (check report)
- `2` — Error (bad arguments or invalid path)

---
