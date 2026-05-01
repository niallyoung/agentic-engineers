# Usage-Tracking Skill: Agent Integration Guide

How agents invoke and use the usage-tracking skill during session work.

---

## When to Invoke (By Agent Role)

### Orchestrator (Primary User)

**Session Start:**
```bash
# Capture baseline usage
bash skills/usage-tracking/scripts/capture_token_usage.sh
```
→ Establishes starting point for session analysis

**Every 30 Minutes (Checkpoints):**
```bash
# Check trends and adjust delegation strategy
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
```
→ Output shows: current%, trend, velocity, hours to reset
→ Decision: GREEN/YELLOW/RED → adjust model tier or task scope

**Before Delegating Major Work:**
```bash
# Verify budget available before assigning task
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq .session.current
```
→ If < 70%: proceed normally (GREEN)
→ If 70-85%: delegate to Engineer with Sonnet (YELLOW)
→ If > 85%: delegate to Haiku only or defer (RED)

**Session End:**
```bash
# Capture final state for daily metrics
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```
→ Included in HANDBACK metrics: tokens consumed, velocity, trend

---

### Engineer (All Roles)

**Before Expensive Operations:**
```bash
# Quick check: can I complete this task with current budget?
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```
Example: Before starting a complex refactor that might need 5K tokens
- If session is 45% and rising 10%/hour → ~4 hours left → proceed
- If session is 85% and rising → defer or use minimal scope

**During Long Task:**
```bash
# Mid-task check: pace sustainable?
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```
→ Captures without voice alert
→ Can query history to see consumption rate

**In HANDBACK Response:**
```markdown
## Metrics
- Model: Haiku (budget-optimized)
- Session before: 45%, after: 52%
- Tokens consumed: ~3,500 (measured)
- Efficiency: 7% session increase for this task
- Trend: stable, no acceleration
```

---

### Quality Engineer

**During Verification:**
```bash
# Check if token consumption was reasonable for work scope
bash skills/usage-tracking/scripts/usage-tracking.sh analyze

# Review consumption rate
# If unusually high: flag with Engineer for review
```

Example anomaly detection:
- Task scope: "Add validation function" (normally ~1-2K tokens)
- Observed consumption: 8K tokens
- Investigation: Does the implementation include unnecessary complexity?

---

### Model Engineer

**For Cost Analysis:**
```bash
# Analyze historical usage patterns
bash skills/usage-tracking/scripts/usage-tracking.sh logs

# Trend analysis for optimization recommendations
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```

---

## Invocation Patterns

### Pattern 1: Silent Capture (No Alert)
```bash
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```
**Use when:** You don't want voice alerts interrupting focus
**Output:** Silently logs to data/metrics/usage_history.jsonl

### Pattern 2: Verbose Capture (With Confirmation)
```bash
VERBOSE=true bash skills/usage-tracking/scripts/capture_token_usage.sh
```
**Use when:** You want confirmation that capture succeeded
**Output:** Prints timestamp, session%, weekly%, status, file path

### Pattern 3: Quick Analysis (Human-Readable)
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```
**Use when:** You need the formatted report with trend visualization
**Output:** Colored status, current/min/max/avg, velocity, forecast

### Pattern 4: Automated Analysis (JSON)
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```
**Use when:** You're parsing in a script or automation
**Output:** Pure JSON with structured data for querying

### Pattern 5: Full Workflow (Capture + Analyze)
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
```
**Use when:** You want one command for "capture and show me now"
**Output:** Voice alert (if threshold) + analysis report

---

## Integration with HANDOFF Protocol

When Orchestrator delegates work with budget awareness:

```markdown
---
DELEGATE

Agent: Engineer
Role: Engineer

Task: Refactor authentication handler (payment_flow.go)
Scope: Medium (~3-5 minutes development, ~2K tokens expected)
Complexity: MEDIUM (complex logic, but isolated from other services)

Budget Status:
Session: 65% (YELLOW) — rising 8.2% per hour, 4.2 hours to reset
Weekly: 42% (GREEN) — stable, adequate weekly budget

Model Assignment: Sonnet (balances capability with efficiency)
Model Rationale: Refactoring task benefits from deep context, Sonnet sufficient for isolated scope

Constraint: Focus on pattern matching; avoid exploring peripheral code paths.

MEASURE: Include token consumption in HANDBACK metrics.

---
ENGINEER WORK
---

[Engineer completes task]

---
HANDBACK

Model used: Sonnet (per assignment)
Session before: 65%
Session after: 71%
Tokens consumed: ~2,100 (estimated: 3K - 900 pattern reuse)
Trend: Rising +6% (slightly faster than predicted, new patterns = more explanation)
Status: GREEN heading to YELLOW (recommend next task be smaller or Haiku)

Quality: ✓ All tests pass, code review ready
Metrics: Efficiency improved vs. baseline (detailed analysis in metrics file)

---
QUALITY ENGINEER VERIFICATION
---

[Verify task meets QUALITY.md requirements]

Is token consumption reasonable?
- Expected: 2-3K for this scope
- Actual: 2.1K
- Assessment: ✓ On target

---
ACCEPTED
```

---

## Data Usage in Decisions

### Budget Awareness
```bash
# Before starting task
STATUS=$(bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq -r .session.status)

if [ "$STATUS" = "RED" ]; then
    # Defer complex work, use Haiku only
    MODEL="haiku"
elif [ "$STATUS" = "YELLOW" ]; then
    # Balance capability with efficiency
    MODEL="sonnet"
else
    # Plenty of budget
    MODEL="sonnet"  # or opus for complex tasks
fi
```

### Velocity-Based Decisions
```bash
# Am I on pace to exceed limits?
VELOCITY=$(bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq '.session.pct_per_hour')
HOURS_LEFT=$(bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq '.session.estimated_reset_in_hours')

# If consuming faster than expected, reduce scope
if (( $(echo "$HOURS_LEFT < 1" | bc -l) )); then
    # Less than 1 hour left, defer non-critical work
    DEFER_TASK=true
fi
```

### Trend Analysis
```bash
# Is consumption accelerating or stabilizing?
TREND=$(bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq -r .session.trend)

if [ "$TREND" = "rising" ]; then
    # Getting more expensive over time (token-heavy operations)
    # Consider: simpler approach, more reuse, delegation to Haiku
    STRATEGY="efficiency"
else
    # Stable or falling (good patterns established)
    # Can continue normally or even escalate scope
    STRATEGY="capability"
fi
```

---

## Common Invocation Scenarios

### Scenario 1: Morning Session Start
```bash
# Orchestrator: establish baseline
bash skills/usage-tracking/scripts/capture_token_usage.sh

# Output: "✓ Captured usage snapshot: Session 0%, Weekly 28%"
# Decision: Green status, proceed with normal planning
```

### Scenario 2: Mid-Session Checkpoint
```bash
# Orchestrator: 30-minute checkpoint
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# Output shows: Session 45%, rising 6% per hour, 9 hours to reset
# Interpretation: GREEN, stable pace, continue normal work
# Next: Delegate task to Engineer with Sonnet
```

### Scenario 3: Approaching Limit
```bash
# Orchestrator: regular checkpoint
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# Output shows: Session 78%, rising 8.2% per hour, 2.7 hours to reset
# Interpretation: YELLOW, accelerating, approaching limit
# Action: Switch to Haiku-only assignments, consider break in ~2 hours
# Next: Delegate small task to Engineer with Haiku assignment
```

### Scenario 4: Engineer Decision Point
```bash
# Engineer: before starting complex feature
bash skills/usage-tracking/scripts/usage-tracking.sh analyze

# Output shows: Session 72%, trend RISING, ~3 hours to reset
# Decision: Estimate 4K tokens needed, but only 3 hours left
# Action: Split into smaller tasks OR request Orchestrator to defer to next session
# Communicate: "Task scope too large for current budget; recommend deferral or split"
```

### Scenario 5: Session Recovery
```bash
# Session reset occurs (automatic)
bash skills/usage-tracking/scripts/capture_token_usage.sh

# Output: "✓ Captured usage snapshot: Session 0%, Weekly 42%"
# Decision: Session refreshed to 0%, continue with full capability
# Model assignment: Reset to Sonnet (standard)
```

---

## Error Handling

### "No usage data captured yet"
**Cause:** First invocation, no history exists
**Fix:** Run capture first:
```bash
bash skills/usage-tracking/scripts/capture_token_usage.sh
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```

### Voice Alert Too Loud/Quiet
**Fix:** Adjust system volume (not controlled by skill):
```bash
# macOS
osascript -e 'set volume output volume 50'  # 50%

# Or disable alerts
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```

### Path Not Found
**Cause:** Running from wrong directory
**Fix:** Run from project root (~/git/ers):
```bash
cd ~/git/ers
bash {service-name}/agentic-engineers/skills/usage-tracking/scripts/usage-tracking.sh analyze
```

---

## Summary: When Agents Call This

| Agent | When | What | Why |
|-------|------|------|-----|
| **Orchestrator** | Session start | capture | Establish baseline |
| **Orchestrator** | Every 30 min | snapshot | Check trends, adjust course |
| **Orchestrator** | Before delegation | analyze --json | Verify budget for task tier |
| **Engineer** | Before expensive ops | analyze | Estimate if budget sufficient |
| **Engineer** | In HANDBACK | analyze | Report consumption metrics |
| **QE** | During verification | analyze | Check reasonableness of consumption |
| **Model Engineer** | Optimization work | logs + analyze | Analyze patterns for recommendations |

---

## See Also

- `SKILL.md` — Complete skill documentation
- `orchestration/USAGE-BUDGET-MANAGER.md` — Real-time budget status
- `orchestration/USAGE-BUDGET-INTEGRATION.md` — Orchestrator workflow
- `orchestration/TOKEN-USAGE-TRACKING.md` — Detailed technical guide
- `orchestration/HANDOFF.md` — DELEGATE/HANDBACK protocol
