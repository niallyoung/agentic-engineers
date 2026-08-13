---
name: spec-management
description: Exclusive governance protocol for all docs/SPEC.md modifications — proposal, impact analysis, multi-role approval, and changelog audit trail. Only Principal/Security/Lead Engineers may invoke it. Prose protocol (no runtime code); the discipline is enforced by role convention and the reviewing agents, not a script.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "2.0"
  category: management
  role: principal-engineer
  authority: principal-engineer, security-engineer, lead-engineer
  model: claude-opus-5
  effort: medium
  thinking: true
---

# spec-management

## Overview

**Governance skill, not runtime code.** `docs/SPEC.md` is the canonical specification;
this skill defines the *process* by which it may change — proposal → impact analysis →
approval → changelog → audit trail — and names who is authorized to run that process.
Only **Principal Engineer**, **Security Engineer**, and **Lead Engineer** may propose or
approve a SPEC.md change; every other agent treats SPEC.md as read-only.

This is the mirror image of `spec-validator` (which is Python and CI-blocking):
spec-validator checks that *implementation* complies with the current SPEC.md;
spec-management governs changes *to* SPEC.md itself.

## The Protocol

### 1. Proposal

Write a proposal file at `docs/spec-proposals/SPEC-YYYY-NNN.yaml` (next sequential
number for the year) with this schema — see any existing file under
`docs/spec-proposals/` for worked examples:

```yaml
change_id: SPEC-2026-NNN
proposer: principal-engineer        # your role
proposer_role: principal-engineer   # duplicated for audit clarity
timestamp: 2026-08-11T00:00:00Z
affected_sections:
  - "Exact SPEC.md section heading(s) touched"
proposed_changes:
  "Exact SPEC.md section heading": |
    Precise description of what changes in that section and why the new
    text is correct — specific enough that an approver can review the
    proposal without diffing SPEC.md by hand.
rationale: |
  Why this change is needed: what's wrong, drifted, or missing today, and
  what problem the change solves.
compatibility_notes: |
  What does NOT change — protocol fields, model IDs, LOCKED sections.
  Breaking changes must be called out explicitly, not implied.
breaking_change: false
```

### 2. Impact Analysis

Before requesting approval, the proposer identifies: which other docs/skills
reference the affected section(s) (`grep` the repo), whether any **LOCKED** SPEC.md
section is touched (LOCKED sections require the sanctioned-edit discipline — see
SPEC.md's own locking note, not a free rewrite), and whether the change is
backward-compatible (default assumption: it must be, unless `breaking_change: true`
is justified in the proposal).

### 3. Approval

Route the proposal for review to at least one other authorized role:

| Proposer | Minimum approval |
|---|---|
| Principal Engineer | Security Engineer (or Lead Engineer for non-security-adjacent changes) |
| Security Engineer | Principal Engineer or Lead Engineer |
| Lead Engineer | Principal Engineer or Security Engineer |

Approval is recorded by the approving role co-authoring the changelog entry (step 4)
— there is no separate approval artifact; the changelog entry itself IS the audit
record of who proposed and who approved.

### 3a. Self-Authorized Narrow Follow-Up (alternative to peer approval)

**When it applies:** the proposal is a narrow, surgical correction (string swaps, stale
references, defect fixes) routed to the proposer by an explicit DELEGATE from the
Orchestrator (or another routing authority), the proposer is Lead/Principal/Security
Engineer, and no LOCKED-section *semantics* change — only accuracy of already-settled
content. Recurring pattern in this repo's own history: SPEC-2026-002 (queue-path-order
residuals), SPEC-2026-005 (framework-slimdown rewrite, sanctioned-edit-only within LOCKED
sections), SPEC-2026-006 (stale harness enumeration). The issuing DELEGATE — not a peer
reviewer — is the authorization: its `task_id` and `ancestry` are already an audited,
routed grant of authority for exactly this scope.

**What replaces the `approval_chain`:** two proposal fields instead of a peer-approval
table:

```yaml
approved_by: lead-engineer          # the proposer's own role — no second approver role
authorization_note: |
  Authorized by routing DELEGATE task-2026-08-12-followup-spec006-queue-harnesses, issued
  by the orchestrator with ancestry back to task-2026-08-11-framework-slimdown-root. No
  separate principal-engineer/security-engineer approval_chain is recorded for this
  change, matching the precedent set by SPEC-2026-002 and SPEC-2026-005.
```

The changelog entry (step 4) is written exactly as in the peer-approval path, e.g.
`[SPEC-2026-006 — lead-engineer, framework slimdown follow-up C]` — there is no
`approved by <role>` clause because none applies; the bracket names only the proposer.

**When it does NOT apply:** any change to a LOCKED invariant's *meaning* — model list
membership, the naming rule itself, recursion/depth limits, the
`.githooks/LOCKED_MODELS.sh` single-source-of-truth clause, or anything that changes what
a reader or validator must do differently. Those still require the full peer
`approval_chain` from step 3, regardless of how narrow the diff looks — narrowness of the
*edit* is not the same as narrowness of its *consequence*.

### 4. Apply + Changelog (the audit trail)

Once approved: edit `docs/SPEC.md` to make the described change, then append one line
to its changelog list (near the end of the document) in this exact format:

```
- **YYYY-MM-DD:** [SPEC-YYYY-NNN — proposer-role, approved by approver-role] One or
  two sentences: what changed and why. See `docs/spec-proposals/SPEC-YYYY-NNN.yaml`.
```

This changelog list, in order, IS the immutable audit trail — every entry is
append-only (never edit or remove a prior entry) and points back to its proposal
file for full detail. `git log -- docs/SPEC.md docs/spec-proposals/` gives the
tamper-evident history on top of that.

### 5. Rollback

To revert a change, propose a new SPEC-YYYY-NNN that restores the prior text —
governed by the identical protocol above, not a special-cased "undo" path. The
changelog entry for the reverting proposal must reference the change_id it reverts.

## Why This Stays Prose

SPEC.md itself names this skill as the exclusive gateway for its own modification
(a LOCKED-adjacent governance constraint) — the protocol's authority comes from
being documented and consistently followed by the three authorized roles, not from
a script enforcing it at runtime. A prior version of this skill had ~2,900 LOC of
Python (`spec_manager.py`, `authorizer.py`, `impact_analyzer.py`, `audit_logger.py`,
etc.) implementing exactly this workflow in code; it was never wired into any
CI gate or invoked by the runtime protocol validators, so it added maintenance
surface without adding enforcement. The actual enforcement mechanisms are:
`spec-validator` (CI-blocking, checks implementation against SPEC.md) and human/agent
review discipline on every PR that touches `docs/SPEC.md`.

## Self-Improvement

This skill participates in the framework's continuous improvement cycle (see
[`skill-improvement-feedback`](../skill-improvement-feedback/SKILL.md)). Include a
`skill_feedback` entry in your HANDBACK when you use `spec-management`:

```yaml
skill_feedback:
  - skill_name: spec-management
    effectiveness_score: 0.85        # required: 0.0-1.0
    coverage_gaps: []
    improvement_suggestions: []
    usage_context: "One sentence on how you used this skill"
```
