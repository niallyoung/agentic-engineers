# Usage Budget Manager Integration Guide

How Orchestrator integrates budget monitoring into the work delegation flow.

---

## Quick Reference

```bash
# Check budget status (human-readable)
./scripts/usage-budget.sh --session 91 --weekly 40 --resets-in 1

# Check in JSON format
./scripts/usage-budget.sh --session 91 --weekly 40 --json

# Check if reset is recommended (shell script friendly)
if ./scripts/usage-budget.sh --check-reset --session 91; then
    echo "Reset not needed"
else
    echo "Reset recommended"
fi
```

---

## Orchestrator Workflow Integration

### Session Startup

```
1. ORCHESTRATOR: Check usage status
   $ ./scripts/usage-budget.sh --session 0 --weekly 35 --resets-in 60

2. OUTPUT:
   ✓ GREEN LIGHT:
     • Use best model for task requirements
     • Plan complex work with Opus if needed

3. ORCHESTRATOR: Log to session context
   [Session context: budget_status=green, session_pct=0, weekly_pct=35]

4. ORCHESTRATOR: Ready for work delegation
```

### Every 30 Minutes (Checkpoints)

```
[30 minutes of work]

ORCHESTRATOR: [Periodic check]
$ ./scripts/usage-budget.sh --session 45 --weekly 38 --resets-in 30

OUTPUT:
✓ GREEN LIGHT:
  • Use best model for task requirements
  • Plan complex work with Opus if needed

ORCHESTRATOR: [Continue normally]
```

### Approaching Limit

```
[More work]

ORCHESTRATOR: [Status check]
$ ./scripts/usage-budget.sh --session 78 --weekly 40 --resets-in 15

OUTPUT:
⚠️ STATUS: MODERATE
  • Bias toward Sonnet; avoid Opus unless critical
  • Use Haiku for routine/well-defined tasks

ORCHESTRATOR: [Adjust delegation strategy]
- Next task → Engineer (smaller, Sonnet-friendly)
- Avoid escalations to Senior/Lead
```

### Critical Limit Approaching

```
[Still more work]

ORCHESTRATOR: [Status check]
$ ./scripts/usage-budget.sh --session 88 --weekly 42 --resets-in 5

OUTPUT:
🛑 ACTION REQUIRED:
  1. Consider pausing for session reset (~1 min)
  2. Or continue with Haiku 4.5 for 1-2 small tasks
  3. Get explicit user approval before proceeding

ORCHESTRATOR → USER:
"Session at 88% budget. 5 minutes until reset.
Current work in progress: none
Pending tasks: 2 refactoring tasks (~2K tokens each)

Options:
A) Pause 5 minutes for reset, continue fresh (recommended)
B) Continue with Haiku for 1-2 more tasks
C) Defer work to next session

Your choice? (A/B/C):"

IF USER CHOOSES B:
  ⚠️⚠️⚠️ MODEL COMPLEXITY REDUCTION BELOW SAVED CONFIG ⚠️⚠️⚠️
  
  Saved config: Sonnet 4.6
  Temporary change: Haiku 4.5 (67% token savings)
  
  Approval? (y/N): _
  
  [WAIT FOR EXPLICIT 'y']
```

### Session Reset

```
ORCHESTRATOR: [Wait 60 seconds]

ORCHESTRATOR: [Check budget after reset]
$ ./scripts/usage-budget.sh --session 0 --weekly 42 --resets-in 60

OUTPUT:
✓ GREEN LIGHT:
  • Use best model for task requirements
  • Plan complex work with Opus if needed

ORCHESTRATOR: [Resume normal delegation]
```

---

## Configuration Integration

### Passing Current Usage to Scripts

**Option 1: Manual from /usage screenshot**

```bash
# User provides: "Session 91%, Weekly 40%, Resets in 1 min"
./scripts/usage-budget.sh --session 91 --weekly 40 --resets-in 1
```

**Option 2: API Query (future)**

```bash
# When /usage API becomes programmatically accessible
# Script can query directly without manual input
USAGE=$(curl -s https://claude.ai/api/usage)
SESSION=$(echo $USAGE | jq .session_percent)
WEEKLY=$(echo $USAGE | jq .weekly_percent)
RESETS=$(echo $USAGE | jq .session_resets_in_minutes)

./scripts/usage-budget.sh --session $SESSION --weekly $WEEKLY --resets-in $RESETS
```

---

## Handoff Protocol

When Orchestrator delegates with budget awareness:

```
ORCHESTRATOR → ENGINEER:

Task: [Code review of PR #123]
Budget: GREEN (session 45%, weekly 38%)
Model: Sonnet (standard)
Effort: MEDIUM
Constraint: None

[Engineer proceeds normally]

---

ORCHESTRATOR → ENGINEER (YELLOW budget):

Task: [Refactor auth flow]
Budget: YELLOW (session 72%, weekly 42%)
Model: Sonnet (prefer efficiency)
Effort: MEDIUM
Constraint: Estimate <3K tokens; use patterns/templates to reduce discussion

[Engineer optimizes for token efficiency]

---

ORCHESTRATOR → HAIKU (RED budget):

Task: [Update docstring]
Budget: RED (session 89%, weekly 45%)
Model: Haiku only
Effort: LOW
Constraint: Well-defined, no complex reasoning

[Haiku handles routine work]
```

---

## User Interaction Points

### Explicit Approval for Model Reduction

When Usage Budget Manager recommends dropping below saved config:

```
Your saved configuration: Sonnet 4.6
Recommended temporary change: Haiku 4.5

Reason: Session 87% used, resets in 3 minutes
Benefits: Save 2K tokens, complete 1-2 more tasks
Risks: Reduced capability, may need re-work

Approve? (y/N): _
```

**Critical:** Only proceed if user types `y` (explicit, case-sensitive).

### Break Recommendations

```
Session at 85% budget, 8 minutes until reset.
Current task: In progress (5 minutes remaining)
Recommendation: Take a 10-minute break after current task completes.

Benefits:
  • Session will reset naturally
  • Return fresh with full budget
  • No forced model reduction

Suggestion: Grab coffee ☕, check email, return at 14:45.
Continue current task? (y/N):
```

---

## Alerting & Notifications

### Escalation Levels

| Level | Trigger | Action |
|-------|---------|--------|
| INFO | Session >60% | Log to context, adjust strategy |
| WARNING | Session >75% | Alert user, suggest break points |
| CRITICAL | Session >85% | Require approval for any new work |
| RESET | Session ≥100% OR session_resets_in=0 | Force reset (automatic) |

### Log Format (CloudWatch/File)

```json
{
  "timestamp": "2026-04-25T14:32:00Z",
  "event": "budget_check",
  "session_pct": 78,
  "weekly_pct": 40,
  "status": "YELLOW",
  "action": "delegated_to_engineer_with_sonnet",
  "session_resets_in_mins": 15
}
```

---

## Limits & Assumptions

### Current Assumptions

1. **Session reset:** Automatic via claude.ai platform (no action needed)
2. **Weekly reset:** Tuesday 6:00 AM UTC (per claude.ai schedule)
3. **Session limit:** 100% (platform enforces)
4. **Weekly limit:** 100% (platform enforces)

### Future Work

- [ ] Programmatic access to /usage API (remove manual input)
- [ ] Per-role budget allocation (Engineer gets 20%, Senior gets 15%, etc.)
- [ ] Cost tracking (tokens → $USD)
- [ ] Predictive alerts ("At current pace, weekly exhausted by Friday")
- [ ] Integration with METRICS.md for historical analysis

---

## Usage-Tracking Skill Integration

**NEW:** Automatic usage capture and historical analysis (replaces manual input).

The `skills/usage-tracking/` skill enables Orchestrator to automatically capture usage snapshots and analyze trends over time, rather than manually entering percentages.

### Quick Integration

**Start of session:**
```bash
bash skills/usage-tracking/scripts/capture_token_usage.sh
```

**Every checkpoint (30 min):**
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
```

Output includes current status (GREEN/YELLOW/RED) + trend forecasting (hours to reset).

**Decision-making:**
```bash
# Before delegating major work
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq .session.current
```

### Orchestrator Workflow with Skill

```
SESSION START:
  Orchestrator: bash skills/usage-tracking/scripts/capture_token_usage.sh
  → logs baseline to data/metrics/usage_history.jsonl

30-MINUTE CHECKPOINT:
  Orchestrator: bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
  → shows current usage + velocity + reset forecast
  → output: "Session 45%, rising 8.2%/hour, reset in 6.9 hours"
  → decision: GREEN → continue normally

45-MINUTE CHECKPOINT:
  Orchestrator: bash skills/usage-tracking/scripts/usage-tracking.sh analyze
  → shows: "Session 65%, rising 9.1%/hour, reset in 3.9 hours"
  → decision: YELLOW → delegate to Engineer with Sonnet (more efficient)

SESSION END:
  Orchestrator: bash skills/usage-tracking/scripts/usage-tracking.sh analyze
  → final stats included in HANDBACK metrics
  → consumed X tokens at Y% per hour
```

### Skill vs. Manual Input

| Aspect | Usage-Budget-Manager (manual) | Usage-Tracking Skill (auto) |
|--------|------|-----|
| Input | Manual from /usage screenshot | Automatic capture |
| Frequency | On-demand checks | Continuous history |
| Trend visibility | Single snapshot | Historical trends + velocity |
| Reset forecast | Manual calculation | Automatic calculation |
| Data retention | Discarded after use | Saved for daily analysis |

**Use the skill:** Enables smarter decisions based on usage velocity and trends.

---

## See Also

- `TOKEN-USAGE-TRACKING.md` — Detailed usage-tracking skill guide
- `../skills/usage-tracking/SKILL.md` — Usage-tracking skill definition
- `USAGE-BUDGET-MANAGER.md` — Budget Manager skill definition
- `scripts/usage-budget.sh` — Shell wrapper (manual budget checking)
- `scripts/usage-budget-check.py` — Core budget logic
- `config/MODEL_ASSIGNMENTS_LOCKED.md` — Saved defaults (never modified by Budget Manager)
