---
name: Phase 5.10 Integration Guide
description: How all components wire together - developers, git hooks, agents, artifacts, decisions
created: 2026-04-28
type: integration-guide
phase: 5.10
---

# Phase 5.10 Integration Guide

## Complete Workflow (Developer Perspective)

```
Developer:
  $ git add .
  $ git commit -m "feat: add new feature"
  
  ↓ [AUTOMATIC - NO USER ACTION]
  
Pre-commit Hook ({workspace-name}/githooks/pre-commit):
  1. Runs thin validation ({service-name} version bump)
  2. Generates DELEGATE block
     - Creates: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}.yaml
     - Contains: repo_path, service_name, commit_sha, budget_context
  3. Runs: make quality-gate
     - This triggers the orchestrator
  4. Hook is silent during orchestrator processing
  5. Polls: artifacts/2026-MM-DD/ for HANDBACK block
     - Timeout: 5 minutes
     - Checks every 1 second
  6. Reads HANDBACK final_decision:
     - If PROCEED: Allow commit ✅
     - If ESCALATE: Reject commit ❌ (print recommendation)

Developer sees:
  ✅ [commit message]
  
OR

  ❌ Quality gate escalated - Review: [recommendation]
  fatal: pre-commit hook failed

```

---

## Artifact Files Flow

### Input: DELEGATE Block (Written by Git Hook)

```
File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}.yaml

Content:
  handoff_type: DELEGATE
  task_id: 2026-MM-DD-commit-{example-service}-{sha}
  timestamp: 2026-MM-DDTHH:MM:SSZ
  repo_path: /home/user/git/ers/{example-service}
  service_name: {example-service}
  commit_sha: {full_sha}
  budget_context:
    session_pct: 45.0
    trend: stable
    recommended_model: sonnet

Created by: Git hook (pre-commit)
Read by: Quality Gate Orchestrator agent
```

### Processing: Parallel Sub-Agent DELEGATE Blocks

```
Quality Gate Orchestrator reads DELEGATE, creates 4 sub-DELEGATEs:

File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}-security.yaml
  → Sent to Security Agent (Opus)
  
File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}-testing.yaml
  → Sent to Testing Agent (Haiku)
  
File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}-metrics.yaml
  → Sent to Metrics Agent (Haiku)
  
File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}-healing.yaml
  → Sent to Healing Agent (Sonnet)
```

### Output: HANDBACK Blocks (Written by Agents)

```
File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}-security.yaml
  Written by: Security Agent
  Read by: Quality Gate Orchestrator
  Content: {status, severity, findings_count, confidence}

File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}-testing.yaml
  Written by: Testing Agent
  Content: {status, unit_tests, coverage, failures}

File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}-metrics.yaml
  Written by: Metrics Agent
  Content: {status, health_score, anomalies}

File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}-healing.yaml
  Written by: Healing Agent
  Content: {status, auto_fixes, escalations, confidence}

Orchestrator waits for ALL 4 HANDBACK blocks (5-min timeout)
```

### Aggregation: Final HANDBACK (Orchestrator Output)

```
File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}.yaml
  Written by: Quality Gate Orchestrator
  Read by: Git hook (pre-commit)
  
Content:
  handoff_type: HANDBACK
  task_id: 2026-MM-DD-commit-{example-service}-{sha}
  timestamp: 2026-MM-DDTHH:MM:SSZ
  status: complete
  final_decision: PROCEED  # or ESCALATE
  audit_trail: [
    {agent: security, status, severity, findings_count},
    {agent: testing, status, coverage, failures},
    {agent: metrics, status, health_score},
    {agent: healing, status, auto_fixes, escalations}
  ]
  recommendation: "All checks passed. Ready to merge." OR "Issues detected: ..."
  attributes:
    trace_id: {uuid}
    total_tokens_used: {sum of all agents}
    escalations_count: {int}
```

### Feedback: Model Engineer Async

```
File: artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}-model-feedback.yaml
  Created by: Quality Gate Orchestrator (async, after HANDBACK written)
  Sent to: Model Engineer Agent
  
File: artifacts/feedback/model-recommendations.jsonl
  Written by: Model Engineer Agent
  Appended to: models/haiku recommended for testing (confidence 0.90)
  
Next commit of same type:
  → Orchestrator uses this recommendation
  → Uses Haiku for Testing Agent (downgraded for cost efficiency)
  → Tracks outcome (PASS/FAIL) to refine confidence
```

### Telemetry: OpenTelemetry Spans

```
File: artifacts/2026-MM-DD/SPAN-{timestamp}-quality-gate-root.yaml
  Root span for entire operation
  
File: artifacts/2026-MM-DD/SPAN-{timestamp}-agent-security.yaml
  Span for Security Agent execution
  
File: artifacts/2026-MM-DD/SPAN-{timestamp}-agent-testing.yaml
  Span for Testing Agent execution
  
File: artifacts/2026-MM-DD/SPAN-{timestamp}-agent-metrics.yaml
  Span for Metrics Agent execution
  
File: artifacts/2026-MM-DD/SPAN-{timestamp}-agent-healing.yaml
  Span for Healing Agent execution
  
File: artifacts/2026-MM-DD/SPAN-{timestamp}-decision-aggregation.yaml
  Span for orchestrator aggregation logic
  
All contain: trace_id, span_id, tokens_used, duration_ms, status, attributes
```

---

## Timing Diagram

```
Time    Event
──────  ─────────────────────────────────────────────────────────────
09:00   Git hook: Write DELEGATE block
        Git hook: Run make quality-gate
        Git hook: Start polling for HANDBACK (timeout: 5 min)

09:00   Quality Gate Orchestrator agent: Detect DELEGATE block
        Orchestrator: Create 4 sub-DELEGATE blocks
        Orchestrator: Start root span

09:00   [Parallel] Security Agent: Detect DELEGATE, start processing
09:00   [Parallel] Testing Agent: Detect DELEGATE, start processing
09:00   [Parallel] Metrics Agent: Detect DELEGATE, start processing
09:00   [Parallel] Healing Agent: Detect DELEGATE, start processing

09:02   Security Agent: Complete scan, write HANDBACK + SPAN
09:04   Testing Agent: Complete tests, write HANDBACK + SPAN
09:02   Metrics Agent: Complete analysis, write HANDBACK + SPAN
09:03   Healing Agent: Complete fixes, write HANDBACK + SPAN

09:04   Orchestrator: All 4 HANDBACK blocks received
        Orchestrator: Run aggregation logic
        Orchestrator: Create SPAN for aggregation
        Orchestrator: Write final HANDBACK block
        Orchestrator: [Async] Create Model Engineer DELEGATE

09:04   Git hook: Detect final HANDBACK block
        Git hook: Read final_decision
        Git hook: Allow commit (PROCEED) or reject (ESCALATE)

09:05   Developer: Commit succeeds ✅ or fails ❌

09:05   Model Engineer Agent: [Async] Detect feedback DELEGATE
09:05   Model Engineer: Analyze tokens, write recommendation
09:05   Model Engineer: HANDBACK stored in artifacts/feedback/
```

Total latency: ~4-5 minutes per commit

---

## Directory Structure

```
.claude/artifacts/
├── 2026-04-28/
│   ├── DELEGATE-2026-04-28T09:00:00Z-commit-{example-service}.yaml
│   ├── HANDBACK-2026-04-28T09:04:35Z-commit-{example-service}.yaml
│   ├── SPAN-2026-04-28T09:00:00Z-quality-gate-root.yaml
│   ├── SPAN-2026-04-28T09:00:15Z-agent-security.yaml
│   ├── SPAN-2026-04-28T09:00:18Z-agent-testing.yaml
│   ├── SPAN-2026-04-28T09:00:22Z-agent-metrics.yaml
│   ├── SPAN-2026-04-28T09:00:25Z-agent-healing.yaml
│   ├── SPAN-2026-04-28T09:04:30Z-decision-aggregation.yaml
│   └── index.json (auto-generated)
│
└── feedback/
    ├── model-recommendations.jsonl
    └── pattern-analysis.jsonl (Phase 7)
```

---

## How Agents Find Their Work

### Pattern 1: Polling (Current)

```
Agent polls artifacts/ every 1 second:
  IF file matches pattern DELEGATE-{timestamp}-{agent_name}.yaml:
    READ and process
    WRITE HANDBACK and SPAN
    EXIT
```

### Pattern 2: File Watching (Future)

```
When artifacts/ is moved to cloud backend (Phase 9+):
  Cloud service notifies agent: "DELEGATE waiting for you"
  Agent wakes up, processes, responds
  (More efficient than polling)
```

---

## Error Handling

### Agent Timeout (> 5 minutes)

```
If agent doesn't return HANDBACK within 5 minutes:
  Orchestrator: Log error
  Orchestrator: Mark agent as "timeout"
  Orchestrator: Escalate (ESCALATE decision)
  Final HANDBACK: final_decision = ESCALATE
  Git hook: Reject commit
  
Developer sees: "Quality gate timeout - escalated"
```

### Agent Crash

```
If agent process crashes:
  Orchestrator: HANDBACK never appears
  Orchestrator: Timeout occurs
  Final HANDBACK: final_decision = ESCALATE
  Git hook: Reject commit
  
Developer: Retry (same commit) or investigate logs
```

### Conflicting Decisions

```
If agents disagree:
  Security Agent: ESCALATE
  Testing Agent: PROCEED
  Metrics Agent: PROCEED
  Healing Agent: PROCEED
  
Orchestrator aggregation logic:
  "Any escalation = final escalation"
  Final HANDBACK: final_decision = ESCALATE
  
Conservative approach: If ANY agent escalates, the whole gate escalates
```

---

## Developer Guide

### For Everyday Use

**You don't need to do anything special.** Phase 5.10 is transparent:

```
$ git add .
$ git commit -m "feat: my new feature"

[Pre-commit hook runs automatically]
[Quality gate orchestrator processes automatically]
[You see result: success or failure]
```

### For Debugging

If your commit is rejected and you want to know why:

```bash
# Check the HANDBACK block
cat .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml

# See the recommendation
grep "recommendation:" .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml

# View audit trail
grep -A 100 "audit_trail:" .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml

# Check individual agent results
cat .claude/artifacts/2026-MM-DD/HANDBACK-*-security.yaml
cat .claude/artifacts/2026-MM-DD/HANDBACK-*-testing.yaml
# etc.
```

### For Experimentation

Want to see how the agents process commits?

```bash
# Monitor in real-time (before committing in another terminal)
watch -n 1 'ls -ltr .claude/artifacts/2026-MM-DD/ | tail -20'

# After commit, analyze the full audit trail
jq . .claude/artifacts/2026-MM-DD/index.json

# Check token usage per agent
grep "total_tokens:" .claude/artifacts/2026-MM-DD/SPAN-*.yaml
```

---

## Testing Phase 5.10

### Success Criteria

1. ✅ 10+ commits proceed through full pipeline
2. ✅ DELEGATE blocks generated for each commit
3. ✅ All 4 sub-agents respond (no timeouts)
4. ✅ HANDBACK blocks contain valid decisions
5. ✅ OpenTelemetry spans recorded for all operations
6. ✅ Git hook correctly interprets HANDBACK
7. ✅ Commits allowed when PROCEED
8. ✅ Commits rejected when ESCALATE
9. ✅ Audit trail complete in artifacts/
10. ✅ Model Engineer recommendations generated

### Test Execution

```bash
# Make 10 commits (at least 5 should PROCEED, at least 1 should ESCALATE)
for i in {1..10}; do
  echo "Test commit $i" >> test-file.txt
  git add test-file.txt
  git commit -m "test(phase-5.10): test commit $i"
  echo "Commit $i status: $?"
done

# Analyze results
echo "PROCEED commits:"
grep "final_decision: PROCEED" .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml | wc -l

echo "ESCALATE commits:"
grep "final_decision: ESCALATE" .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml | wc -l

echo "Total tokens used:"
grep "total_tokens_used:" .claude/artifacts/2026-MM-DD/HANDBACK-*.yaml | awk '{sum += $2} END {print sum}'
```

---

## Next: Phase 6 (Feedback Loops)

Once Phase 5.10 is validated:
- Feedback loops close (sub-agents → orchestrator → next decision)
- Pattern recognition analyzes recurring issues
- Model Engineer continuously optimizes recommendations
- Metrics collection dashboard becomes operational
- Self-sustaining improvement loop begins

See `TODO.md` Phase 6 section for details.

