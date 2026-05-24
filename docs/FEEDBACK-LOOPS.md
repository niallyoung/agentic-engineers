---
title: Post-Merge Feedback Loops
description: How QE, Security, and post-merge findings trigger re-delegation and drive continuous improvement.
version: 1.0
updated: 2026-05-24
status: Authoritative
---

# Post-Merge Feedback Loops

**Scope:** How quality and security findings after merge flow back into the engineering pipeline  
**Audience:** Orchestrators, QE agents, Lead Engineers, Security Engineers  

---

## Overview

Findings don't stop at the pre-merge gate. After code merges, production monitoring, QE regression runs, and security scans may surface new issues. This document defines the **feedback trigger pattern** — how findings generate new DELEGATE blocks and re-engage the appropriate agents.

```
MERGE
  │
  ├─► QE regression run           ──► finding? ──► new DELEGATE to Engineer
  ├─► Security scan (SAST/DAST)   ──► finding? ──► new DELEGATE to Security Engineer
  ├─► Production monitoring       ──► alert?   ──► new DELEGATE to Healing Engineer
  └─► Model efficiency review     ──► finding? ──► new DELEGATE to Model Engineer
```

---

## Feedback Trigger Pattern

A **feedback trigger** is a structured DELEGATE block generated in response to a post-merge finding. It follows the standard DELEGATE/HANDBACK protocol but carries additional `feedback_context` fields that document the triggering event.

### Feedback DELEGATE Schema

```yaml
---
handoff_type: DELEGATE
task_id: YYYY-MM-DD-<original-task-id>-feedback-<N>
timestamp: <iso8601>
role: <Engineer|Security Engineer|Lead Engineer|...>
model: <model-id>
effort: <low|medium|high>

# Standard fields
scope: >
  <Description of the fix needed, derived from the finding>

# Feedback-specific fields (all required for feedback triggers)
feedback_context:
  trigger: qe_finding | security_scan | production_alert | model_review | manual
  original_task_id: <task-id-that-produced-the-merged-code>
  original_pr: <PR number if applicable>
  finding_type: <bug | regression | vulnerability | performance | cost>
  finding_severity: critical | high | medium | low
  finding_description: >
    <Exact description of what was found, with evidence>
  finding_source: <QE regression suite | SAST scan | Grafana alert | etc.>
  merge_date: <ISO date of the merge that introduced the issue>
  blocks_deployment: true | false

context:
  - <file/component affected>
  - <reproduction steps or log evidence>
  - <any related PRs or commits>

success_criteria:
  - <Testable criterion 1>
  - <Testable criterion 2>

has_plan: false
estimated_complexity: <low|medium|high>
---
```

---

## Feedback Loop Scenarios

### Scenario 1: QE Finds a Regression

**Trigger:** QE agent runs regression suite after merge; tests fail that previously passed.

**Flow:**
```
merge → QE regression run → FAIL
  └─► Orchestrator creates feedback DELEGATE
       ├─► role: Engineer (if regression is straightforward)
       ├─► role: Senior Engineer (if root cause is unclear)
       └─► feedback_context.trigger: qe_finding
```

**Example DELEGATE:**
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-24-add-cursor-sync-feedback-1
timestamp: 2026-05-24T18:00:00Z
role: Engineer
model: claude-haiku-4.5
effort: medium
scope: >
  Fix regression in cursor sync: test_cursor_position_after_reload fails after
  merge of PR #142 (add-cursor-sync). Cursor position reverts to 0 after page
  reload instead of preserving last position.

feedback_context:
  trigger: qe_finding
  original_task_id: 2026-05-23-add-cursor-sync
  original_pr: 142
  finding_type: regression
  finding_severity: high
  finding_description: >
    test_cursor_position_after_reload was passing before PR #142. After merge,
    CursorStore.restore() calls localStorage.getItem() before store hydration,
    returning null instead of the saved position.
  finding_source: QE regression suite (tests/test_cursor_sync.py)
  merge_date: "2026-05-24"
  blocks_deployment: true

context:
  - src/cursor/cursor_store.py (lines 45-67, restore() method)
  - tests/test_cursor_sync.py::test_cursor_position_after_reload
  - Original PR: https://github.com/org/repo/pull/142

success_criteria:
  - test_cursor_position_after_reload passes
  - No new test regressions introduced
  - Original PR test suite still passes

has_plan: false
estimated_complexity: medium
---
```

---

### Scenario 2: Security Scan Finds a Vulnerability

**Trigger:** Post-merge SAST/DAST scan identifies a security issue in merged code.

**Flow:**
```
merge → security scan → VULNERABILITY FOUND
  └─► Orchestrator escalates to Security Engineer
       ├─► feedback_context.trigger: security_scan
       ├─► finding_severity: critical | high (always escalated)
       └─► blocks_deployment: true (if high/critical)
```

**Escalation rules for security findings:**

| Severity | Assignee | blocks_deployment | SLA |
|----------|---------- |-------------------|-----|
| critical | Security Engineer | true | immediate |
| high | Security Engineer | true | 4 hours |
| medium | Lead Engineer | false | next sprint |
| low | Engineer | false | backlog |

**Re-review gate:** After the security fix is merged, Security Engineer must provide a HANDBACK confirming the vulnerability is resolved before deployment unblocks.

---

### Scenario 3: QE Finding Triggers Security Re-Review

**Trigger:** QE finds a bug that may have security implications. QE escalates to Security for review before unblocking the merge.

**Flow:**
```
QE HANDBACK (status: blocked, reason: potential_security_issue)
  └─► Orchestrator creates security review DELEGATE
       ├─► role: Security Engineer
       ├─► feedback_context.trigger: qe_finding
       ├─► feedback_context.finding_type: vulnerability
       └─► Original QE HANDBACK attached as context
  └─► Security Engineer reviews and returns HANDBACK
       ├─► status: approved → unblock merge
       └─► status: blocked → Engineer must fix before merge
```

**Example chain:**
```
DELEGATE(Engineer) → HANDBACK(Engineer, complete) 
  → DELEGATE(QE) → HANDBACK(QE, blocked: security_concern)
    → DELEGATE(Security) → HANDBACK(Security, approved OR blocked)
      → [merge unblocked OR Engineer re-delegated]
```

---

### Scenario 4: Production Alert

**Trigger:** Grafana/CloudWatch alert fires in production, traced to a recently merged change.

**Flow:**
```
production alert → identify causative commit → Orchestrator creates DELEGATE
  └─► role: Healing Engineer (if infrastructure/ops)
  └─► role: Senior Engineer (if code logic)
  └─► feedback_context.trigger: production_alert
```

**SLA for production alerts:**
- P0 (service down): immediate DELEGATE, Senior/Principal Engineer
- P1 (degraded): within 30 minutes, Senior Engineer
- P2 (warning): next work cycle, Engineer

---

### Scenario 5: Model Efficiency Review

**Trigger:** Model Engineer or TokenAdvisor skill identifies a task that was over-engineered (e.g., high-effort task routed to expensive model that could have used Haiku).

**Flow:**
```
Model Engineer review → efficiency gap identified
  └─► feedback_context.trigger: model_review
  └─► role: Model Engineer → HANDBACK with routing recommendation
       └─► Orchestrator updates routing rules for similar future tasks
```

---

## Feedback Loop Protocol Fields

### HANDBACK fields for findings

When a QE or Security agent returns a HANDBACK with a finding that requires re-delegation, they include:

```yaml
---
handoff_type: HANDBACK
task_id: <original-task-id>
timestamp: <iso8601>
status: blocked   # NOT complete — block pipeline until resolved

blocked_by:
  reason: qe_regression | security_vulnerability | integration_failure
  severity: critical | high | medium | low
  description: >
    <Exact description of what is blocking merge>
  evidence:
    - "<test name or log line>"
    - "<reproduction steps>"
  requires_re_delegation: true
  suggested_assignee: Engineer | Senior Engineer | Security Engineer

quality_score: <0-100>
confidence: 0.0
---
```

### Orchestrator's responsibility on blocked HANDBACK

When Orchestrator receives a HANDBACK with `status: blocked` and `requires_re_delegation: true`:

1. **Do not mark the original task as complete**
2. **Create a new feedback DELEGATE** with `feedback_context` populated from the blocking HANDBACK
3. **Track the chain**: `task_id` should reference the original task (e.g., `<original-id>-feedback-1`)
4. **Retry limit**: maximum 2 feedback iterations per original task; if still blocked after 2, escalate to Lead Engineer or Principal Engineer

```yaml
# Retry limit enforcement
feedback_context:
  retry_count: 1        # incremented with each feedback DELEGATE
  max_retries: 2        # if retry_count >= max_retries → escalate
  escalate_to: Lead Engineer
```

---

## Feedback Loop Registry

Feedback DELEGATEs are stored in:
```
artifacts/delegates/YYYY-MM-DD/
  └─ <task-id>-feedback-<N>.yaml
```

And tracked in `TODO.md` with `[FEEDBACK]` prefix:
```markdown
- [ ] [FEEDBACK] Fix regression from PR #142: cursor position reverts on reload
```

---

## Integration with CI/CD

### Automatic feedback triggers from test failures

In CI, a failed test suite post-merge should produce a feedback DELEGATE automatically:

```yaml
# .github/workflows/post-merge-feedback.yml
on:
  push:
    branches: [main]

jobs:
  regression-check:
    steps:
      - run: make test
      - if: failure()
        run: |
          # Orchestrator creates feedback DELEGATE from CI context
          echo "Test failures detected — feedback DELEGATE required"
```

### Deployment gate integration

For `blocks_deployment: true` findings, the deployment pipeline should check for unresolved feedback DELEGATEs:

```bash
# Pre-deploy check (example)
open_feedback=$(find artifacts/delegates -name "*-feedback-*.yaml" \
  -newer dist/.last-deploy \
  -exec grep -l "blocks_deployment: true" {} \;)

if [ -n "$open_feedback" ]; then
  echo "❌ Deployment blocked: unresolved feedback DELEGATEs"
  exit 1
fi
```

---

## Summary: Feedback Trigger Decision Tree

```
Finding discovered (post-merge)
│
├─► Is it a security vulnerability?
│    ├─► YES → DELEGATE to Security Engineer
│    │         blocks_deployment: true (if high/critical)
│    └─► NO  → continue
│
├─► Is it a test regression?
│    ├─► YES → DELEGATE to Engineer (root cause known)
│    │         OR Senior Engineer (root cause unclear)
│    └─► NO  → continue
│
├─► Is it a production alert?
│    ├─► YES (P0/P1) → DELEGATE to Senior Engineer (urgent)
│    └─► YES (P2)    → DELEGATE to Engineer (next cycle)
│
├─► Is it a model efficiency gap?
│    └─► YES → DELEGATE to Model Engineer (recommendation)
│
└─► Unclear/complex finding?
     └─► → Escalate to Lead Engineer for triage
```

---

*See also: [docs/WORKFLOW.md](WORKFLOW.md) for full SDLC gates, [docs/RENDERING.md](RENDERING.md) for render pipeline lifecycle.*
