# Quick Start: Budget Checking

**Time to complete:** 5 minutes  
**Prerequisite:** OpenCode harness installed (`make install-opencode`)

---

## Overview

Budget checking lets you set token limits and get warnings before you exceed them. This prevents runaway costs during long autonomous sessions.

---

## Step 1: Check Current Budget Status

```bash
# Check budget against a limit (200k tokens)
opencode-budget --session <session-id> --limit 200000

# Example output:
# Session: abc123
# Budget limit: 200,000 tokens
# Used: 137,000 tokens (68.5%)
# Remaining: 63,000 tokens (31.5%)
# Status: ✅ WITHIN BUDGET
# Estimated tasks remaining: ~4 (at current avg 15k/task)
```

---

## Step 2: Set a Budget Alert Threshold

```bash
# Alert when 80% of budget is consumed
opencode-budget --session <session-id> --limit 200000 --alert-at 80

# Alert when within 20k tokens of limit
opencode-budget --session <session-id> --limit 200000 --alert-remaining 20000
```

---

## Step 3: Monitor Budget Continuously

```bash
# Check every 60 seconds, alert at 80%
watch -n 60 'opencode-budget --session <session-id> --limit 200000 --alert-at 80'
```

---

## Step 4: Set Budget in DELEGATE

Include budget constraints in your DELEGATE tasks:

```yaml
handoff_type: DELEGATE
task_id: 2026-05-17-my-task
role: Engineer
model: claude-haiku-4-5
effort: medium
scope: |
  Implement the new API endpoint.
context:
  - Budget constraint: 50,000 tokens max for this task
  - If approaching limit, stop and report status: blocked
success_criteria:
  - Implementation complete
  - Tests passing
  - Token usage under 50,000
```

---

## Budget Allocation by Task Type

| Task Type | Recommended Budget |
|-----------|-------------------|
| Simple bug fix | 10,000–20,000 tokens |
| Feature implementation | 30,000–80,000 tokens |
| Code review | 15,000–30,000 tokens |
| Architecture analysis | 50,000–100,000 tokens |
| Security audit | 80,000–150,000 tokens |
| Full session | 150,000–300,000 tokens |

---

## What to Do When Budget is Exceeded

1. **Stop the current task** — set `status: blocked` in HANDBACK
2. **Report what was completed** — partial results are valuable
3. **Estimate remaining work** — how many more tokens needed?
4. **Orchestrator decides** — continue with increased budget, or scope down

```yaml
handoff_type: HANDBACK
task_id: 2026-05-17-my-task
agent: Engineer
status: blocked
quality_score: 60
result: |
  Completed 3 of 5 planned steps. Stopped at step 4 (test writing)
  due to approaching token budget limit.
  Steps 1-3: Implementation complete.
  Steps 4-5: Tests and docs not yet written.
next_steps: |
  Allocate additional 20,000 tokens to complete test writing and documentation.
```

---

## Cost Reference

Approximate token costs (as of May 2026):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-haiku-4-5 | $0.25 | $1.25 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-opus-4-6 | $15.00 | $75.00 |

**Rule of thumb:** A typical Engineer task (Haiku, 20k tokens) costs ~$0.03. A typical Senior Engineer task (Sonnet, 40k tokens) costs ~$0.30.

---

## Related Documentation

- [docs/QUICK-START-TOKEN-VISIBILITY.md](QUICK-START-TOKEN-VISIBILITY.md) — Monitor token usage
- [docs/USAGE-BUDGET-MANAGER.md](USAGE-BUDGET-MANAGER.md) — Full budget manager reference
- [docs/USAGE-BUDGET-INTEGRATION.md](USAGE-BUDGET-INTEGRATION.md) — Budget integration with Orchestrator
- [docs/TOKEN-COST-MONITORING.md](TOKEN-COST-MONITORING.md) — Full monitoring reference
