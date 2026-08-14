---
name: audit-trail-review
description: Reviews the orchestration audit trail (JSONL ledger) for unfinished delegations, orphaned work, and status inconsistencies. Primary input is ~/.agentic-engineers/{harness}/{session-id}/audit/events-*.jsonl; operates on the current session only.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0.1"
  category: meta-skill
  role: quality-engineer
  model: claude-sonnet-5
  effort: medium
---

## Overview

Audit-Trail-Review is a meta-skill that audits the **current session's orchestration ledger** (the append-only JSONL written by `scripts/audit_append.py`) for completeness and consistency. It is designed to run when no agents are in flight and identifies:

1. **Orphaned/Unfinished Delegations** — `delegate_issued`/`subagent_spawned` events with NO corresponding `handback_received`
2. **Unfinalized Acceptances** — `handback_received` events with NO subsequent `gate_result`
3. **Dropped Work** — Status `blocked`, `failure`, or `escalate` with NO subsequent re-route/re-issue/rework event
4. **Unvisited Refusals & Limit Breaches** — `refusal` and `limit_exceeded` events never followed by corrective action
5. **Working-Tree Orphans** — WIP artifacts and TODO/FIXME markers tied to task_ids not in the ledger

This skill is **READ-ONLY** over the audit trail; findings name suggested fixes. It is **SINGLE-SESSION** by design (never enumerates sibling sessions or other harnesses).

## Scope & Architecture

**Single-Session Constraint (MUST):**
This skill operates ONLY on the current harness + current session directory, resolved exactly as `scripts/audit_append.py` resolves it:
- Priority: `AGENTIC_SESSION_ID` env var > `CLAUDE_SESSION_ID` > `COPILOT_SESSION_ID`
- Path: `~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl`

**Why:** Cross-session/cross-harness aggregation is explicitly out of scope to avoid conflating unrelated work. A session is the atomic unit of operation; mixing sessions hides dependencies and creates false findings.

**Companion Tool:** `scripts/handback_rollup.py --events` provides a metrics-rolled-up view over the same events file (tokens, cost, quality); this skill provides the compliance/completeness view.

## Procedure: Ledger Reconciliation

The audit runs in the following order:

### 1. Parse Events File

Load the session's current events JSONL from:
```
~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl
```

Format: one JSON object per line; required fields per SPEC.md clause 7:
- `ts` (ISO-8601 UTC timestamp)
- `event` (string: `delegate_issued`, `subagent_spawned`, `handback_received`, `gate_result`, `escalation`, `refusal`, `limit_exceeded`)
- `task_id` (required)
- `parent_task_id` (may be null for root tasks)
- `depth` (integer)
- `agent_role` (string)
- `agent_model` (string)
- `status` (one of: `success`, `failure`, `partial`, `blocked`, `escalate`)
- `tokens`, `cost` (floats, present on handback_received onwards)

### 2. Build Ledger Index

Create a task-centric index:
```python
ledger[task_id] = {
  "root_event": delegate_issued,
  "spawned": subagent_spawned or None,
  "handback": handback_received or None,
  "gate": gate_result or None,
  "escalation": escalation or None,
  "refusal": refusal or None,
  "limit": limit_exceeded or None,
  "status": [blockers found]
}
```

### 3. Find Orphaned Delegations

Check for incomplete state machines:

**Orphaned/Unfinished:**
- A `delegate_issued` event exists, but no `handback_received` follows it
- `subagent_spawned` (if present) is corroboration; orphan detection keys off `delegate_issued` alone, not the presence of a spawn event (maiden run: 5 of 7 real dispatches lacked `subagent_spawned` in the ledger; a check requiring it would have missed them)
- This blocks reconciliation; the task is presumed active, in flight, or crashed
- **Action:** If orphaned for > 30 minutes: escalate to orchestrator or mark `status: requires-recovery`

**Unfinalized Acceptance:**
- `handback_received` exists, but NO `gate_result` follows
- The HANDBACK was logged but the gate (ORCHESTRATOR acceptance/rejection) never executed
- **Action:** Escalate; gate logic may have crashed

**Dropped Work:**
- Status `failure`, `blocked`, or `escalate` with NO subsequent re-route/re-issue/rework event
- A task is only classified as DROPPED if no remediation is found via (checked in order): (i) a later event carrying `resolves_task_id` pointing at it (the new optional field; see SPEC.md clause 7); (ii) heuristic — a subsequent `delegate_issued` sharing `parent_task_id` within ~30 minutes whose role plausibly remediates (engineer/senior-engineer after a quality-engineer failure, or lead-engineer after a senior-engineer escalation); (iii) git-log cross-check for commit messages citing both task_ids.
- **Example (false positive remediation):** Maiden run found final-consistency-audit (QE task) marked as DROPPED, but audit-findings-fixes (engineer task) remediated it 57ms later under a different task_id — linkage visible only in the commit message, caught by check (iii) above.
- **Action:** Audit the escalation path; verify the owner knows about it

**Unvisited Refusal:**
- `refusal` event (DELEGATE rejected, e.g., protocol guard, scope too vague) with NO follow-up re-route
- **Action:** Trace why the refusal happened and whether the submitter was notified

**Unvisited Limit Breach:**
- `limit_exceeded` event (depth or fan-out limit hit) with NO recovery attempt
- **Action:** Investigate whether the task should be retried at a lower depth or split

### 4. Cross-Check Working Tree

For all unfinished task_ids (those with no `gate_result`), search the working tree for artifacts:

**Searches:**
- `grep -r {task_id}` in working tree (TODOs, comments, backlog references)
- `find . -name "*.bak" -o -name "*.patch" -o -name "*scratch*"` + correlate to task_ids
- Unreferenced fixtures, temporary files, WIP branches

**Finding:** If a task has no `gate_result` but artifacts exist, classify:
- **Legitimate WIP** — marked `backlog: WP-6` or similar; fine
- **Orphaned Artifact** — no backlog home; needs cleanup or re-delegation
- **Stale Marker** — work was completed, marker forgotten; delete

### 5. Reconciliation Report

Output a structured report:

```yaml
---
audit_session: {harness} / {session-id}
timestamp: [ISO-8601 UTC]
ledger_file: ~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl
event_count: N

findings:
  orphaned_delegations: [list]
  unfinalized_acceptances: [list]
  dropped_work: [list]
  unvisited_refusals: [list]
  unvisited_limit_breaches: [list]
  ledger_integrity: [list]
  orphaned_artifacts: [list]

summary: |
  X orphaned delegations (O: unfinished, U: unfinalized, D: dropped,
  RF: unvisited refusal, LB: unvisited limit breach)
  Y orphaned working-tree artifacts
  Recommendation: [healthy | investigate | requires-recovery | escalate]

---
```

## Campaign Audit (Branch-Level)

When run over a completed branch (not the live session), audit-trail-review ALSO supports the 5 **campaign audit mandates** from the pre-merge methodology:

1. **Consistency & Doc Accuracy** — Configuration stories, count verification, capability claims vs implementations, cross-file consistency
2. **Unfinished Work** — TODO/FIXME/flagged-item classification, legitimately-deferred vs in-scope-unfinished vs stale, orphan-artifact hunt
3. **Claim-vs-Disk Truth** — Verify HANDBACK claims against current bytes; detect phantom-success; verify governance-scope; check self-classified failures are reproducible
4. **Privacy** — Session records outside repo; task_id citations are legitimate; embedded bodies/metrics are findings
5. **Quality Re-Check** — Re-run full gate battery, spot-check renders, verify both security-gate strings

These are **secondary** — invoked only on request or as part of a pre-merge audit, not the default session-ledger procedure.

## Invocation

**Illustrative command shape — no CLI implementation exists; follow the Procedure steps manually.**

### Live Session (default)

```bash
# Review the current session's audit trail
python3 -m agentic_engineers.skills.audit_trail_review [--session-id ID] [--harness HARNESS]
# If --session-id / --harness not provided, uses env vars (AGENTIC_SESSION_ID, CLAUDE_SESSION_ID, COPILOT_SESSION_ID, HARNESS)
```

### Branch/Campaign Audit (pre-merge)

```bash
# Audit a completed branch for campaign-audit mandate compliance
python3 -m agentic_engineers.skills.audit_trail_review --mode campaign --branch main...HEAD [--spec docs/SPEC.md]
# Outputs: consistency check, unfinished-work hunt, claim-vs-truth verification, privacy audit, quality re-check
```

## Output Formats

### Live Session Report (default)

```yaml
---
audit_session: claude / abc123def456
timestamp: 2026-08-14T22:45:00Z
ledger_file: ~/.agentic-engineers/claude/abc123def456/audit/events-2026-08-14.jsonl
event_count: 47

findings:
  orphaned_delegations:
    - task_id: task-2026-08-14-foo
      root_event: delegate_issued at 2026-08-14T22:10:00Z
      problem: "subagent_spawned recorded; no handback_received after 35 minutes"
      recommendation: "check if agent is active; if > 60 min, escalate to orchestrator"

  unfinalized_acceptances: []
  dropped_work: []
  unvisited_refusals: []
  unvisited_limit_breaches: []

  orphaned_artifacts:
    - path: "src/skills/new-skill/SKILL.md"
      marker: "TODO: register in src/SKILLS.md"
      related_task: "task-2026-08-14-foo"
      classification: "LEGITIMATE-WIP (backlog: WP-6)"

summary: |
  1 orphaned delegation (active subagent, 35 min old)
  1 orphaned artifact (marked as legitimate backlog)
  Recommendation: HEALTHY - monitor the active subagent; if it persists > 60 min, escalate.

---
```

### Campaign Audit Report (branch mode)

```yaml
---
audit_campaign: main...HEAD
timestamp: 2026-08-14T22:45:00Z
mode: campaign
summary: |
  Consistency: 3 findings (doc drift, count mismatch)
  Unfinished work: 0 in-scope-unfinished, 2 legitimately-deferred
  Claim-vs-truth: 1 phantom-success detected
  Privacy: PASS
  Quality: 1 test regression found
  Verdict: FAIL (must fix phantom-success + regression before merge)

findings: [detailed list per mandate, see Campaign Audit section]

---
```

## Operating Rules

1. **Read-Only Audit** — Auditor produces findings and ranked suggestions; it MUST NOT edit the ledger or working tree; fixes are escalated to the orchestrator or engineer.

2. **Evidence-Based** — Every finding is grounded in an event, a task_id, or a file:line reference.

3. **Single-Session Constraint** — Never enumerate sibling sessions or other harnesses; this prevents conflating unrelated work.

4. **30-Minute Orphan Threshold** — Delegations orphaned for < 30 minutes may still be in flight; > 30 minutes is presumed a crash or hang. The threshold is measured against the auditor's own wall clock at run time (`date -u`), not the ledger file's mtime.

5. **Severity Ranking:**
   - **CRITICAL** (blocks session): unfinalized acceptance, unrecoverable orphan (> 60 min)
   - **HIGH** (requires action): orphaned delegation (30-60 min), dropped work, unvisited limit breach
   - **MEDIUM** (should investigate): orphaned artifact, unvisited refusal
   - **LOW** (informational): WIP artifacts marked as legitimate backlog

6. **Verdict:**
   - **HEALTHY** — No orphaned delegations, all work finalized, no unvisited failures
   - **INVESTIGATE** — Orphaned delegations < 30 min old, or unvisited refusals with no corrective action
   - **REQUIRES-RECOVERY** — Orphaned > 60 min or unfinalized acceptance; escalate to orchestrator
   - **ESCALATE** — Campaign audit mandate violations; escalate findings to lead-engineer

## Known-Legitimate List

Items that are historical and exempt from "slop" findings:
- SPEC.md Update Log entries (all immutable)
- LOCKED SPEC sections (unchanged unless by spec-management proposal)
- Backlog-marked task_ids with an explicit WP-* reference
- Escalation events (refusal, limit_exceeded) when followed by a corrective re-route within the same session

## Self-Improvement

See [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md) for feedback pattern.
Include `skill_feedback` in audit report when this meta-skill's ledger reconciliation or campaign procedures need refinement.
