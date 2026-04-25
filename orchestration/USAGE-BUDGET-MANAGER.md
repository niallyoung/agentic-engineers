# Usage Budget Manager — Real-Time Token Budget Tracking

Real-time token budget awareness and dynamic model adjustment recommendations. Monitors session and weekly usage limits, suggests temporary model changes, and ensures we maximize efficiency within constraints.

---

## Purpose

The Usage Budget Manager provides Orchestrator with:

1. **Real-time visibility** into current session usage vs. reset countdown
2. **Weekly budget tracking** for all-models combined usage
3. **Intelligent recommendations** to maximize within budget
4. **Warnings and escalations** before hitting limits
5. **Temporary adjustment suggestions** (model tier, effort level, break time)

All adjustments are **temporary per-session only** and never modify saved configuration in `.md` files.

---

## How It Works

### Session-Level Monitoring

Every 15-30 minutes during active work:

```
Current Session Usage: 91% used
Resets in: 1 minute
Status: ⚠️ APPROACHING LIMIT

Recommendation:
  - Current model: Sonnet 4.6
  - You have ~9% budget remaining (~1,200 tokens)
  - Options:
    A) PAUSE & RESET (recommended) — Take a 60s break, session resets
    B) CONTINUE with Haiku 4.5 (50% fewer tokens) — 2-3 more small tasks
    C) CANCEL pending work — Defer to next session

⚠️ NOTE: Option B reduces model complexity below your Sonnet setting.
Do you want to continue with Haiku? (y/N):
```

### Weekly Budget Monitoring

At session start (and hourly during long sessions):

```
Weekly Budget Status: 40% used (all models)
Resets: Tuesday 6:00 AM (18 hours away)

Budget consumed:
  - This week: 40,000 tokens
  - Budget: 100,000 tokens
  - Remaining: 60,000 tokens

You're in the green. Proceed normally with Sonnet/Opus for complex tasks.
```

### Dynamic Adjustment Logic

**GREEN (0-60% usage):**
- Use best model for task complexity
- Sonnet for moderate tasks, Opus for hard planning/architecture
- Haiku for simple, well-defined tasks

**YELLOW (60-85% usage):**
- Bias toward Sonnet (faster, cheaper)
- Haiku for routine tasks
- Avoid Opus unless critical

**RED (85%+ usage):**
- Haiku only
- Consider breaking work across sessions
- Option to pause and reset

---

## Integration with Orchestrator

Orchestrator checks Usage Budget Manager when:

1. **Session starts** — Get weekly + session status
2. **Every 30 minutes** (configurable) — Check session usage
3. **Before delegating expensive tasks** — Verify budget headroom
4. **On request** — "Usage Budget Manager: report status"

### Example Handoff

```
ORCHESTRATOR: [Check budget]
USAGE BUDGET MGR: Weekly 40%, Session 91%. Session resets in 1 min.

ORCHESTRATOR: [Wait 60 seconds for reset]
SESSION RESET

ORCHESTRATOR: [Check budget again]
USAGE BUDGET MGR: Weekly 40%, Session 0%. Proceed.

ORCHESTRATOR: [Plan today's work within budget]
```

---

## Configuration (Session-Only)

These are temporary overrides for this session only. Not saved to `.md`.

```yaml
# Session overrides (this session only)
session_model_override: "haiku"  # Temporarily use Haiku instead of Sonnet
session_effort_override: "low"    # Temporarily reduce effort level
session_break_suggested: true     # Suggest a pause to reset

# These do NOT modify config/MODEL_ASSIGNMENTS_LOCKED.md
# Next session, we return to saved defaults
```

---

## Warning System

**LOUD WARNINGS** when considering reductions:

```
⚠️⚠️⚠️ MODEL COMPLEXITY REDUCTION BELOW SAVED CONFIG ⚠️⚠️⚠️

Your saved configuration in config/MODEL_ASSIGNMENTS_LOCKED.md:
  - Default model: Sonnet 4.6
  - Preferred: Opus 4.7 for complex planning

I'm recommending temporary reduction to:
  - Model: Haiku 4.5 (saves 67% tokens)
  - Reason: Session 88% used, resets in 8 minutes

RISKS:
  ✗ Reduced capability for complex reasoning
  ✗ May need re-work or escalation if task fails
  ✗ Slower execution

BENEFITS:
  ✓ Stay within session budget
  ✓ Avoid forced pause/reset
  ✓ Complete 1-2 more tasks

DECISION REQUIRED: Approve reduction? (y/N):
  y — Yes, temporarily use Haiku for this session
  N — No, wait for session reset instead
  ? — Show me the math
```

**No reduction happens without explicit user `y` response.**

---

## Data Source

Usage Budget Manager queries from:

1. **claude.ai /usage endpoint** (programmatic access via API)
   - Current session: %used, time to reset
   - Weekly: %used, time to reset
   - Plan limits: session cap, weekly cap

2. **Alternative:** Manual input from screenshot/UI
   - User provides current usage percentages
   - Budget Manager calculates recommendations

---

## Skill Implementation

**Role:** Orchestrator (owns budget awareness)  
**Model:** Haiku 4.5 (lightweight, real-time)  
**Effort:** Low (simple math, rule-based)  
**Invocation:** Every 30 min (automatic) or on-demand

### File Structure

```
skills/usage-budget/
├── SKILL.md (this file)
├── scripts/
│   ├── check-budget.sh (query /usage)
│   ├── calculate-recommendations.py (decision logic)
│   └── format-report.py (pretty output)
└── references/
    └── usage-limits.md (static: session/weekly caps)
```

---

## Example Workflow

**Time: 14:45, Session 30 minutes in**

```
ORCHESTRATOR: [30-min check]
USAGE BUDGET MGR: Session 45%, Weekly 35%. Green. Proceed with Sonnet.

ORCHESTRATOR → ENGINEER: [Delegate code review task]
[10 minutes later]

ORCHESTRATOR: [45-min check]
USAGE BUDGET MGR: Session 78%, Weekly 38%. Yellow. Next task → Haiku?

ORCHESTRATOR: [Assigns lightweight refactor to Engineer]
[5 minutes later]

ORCHESTRATOR: [50-min check]
USAGE BUDGET MGR: Session 91%, Weekly 40%. RED. Session resets in 1 min.

ORCHESTRATOR → USER:
"Session nearly full (91%). Recommend pause 60 seconds for reset.
Pending work: 2 small tasks (cost ~2K tokens each). 
After reset, we'll have room. Continue? (y/N)"

USER: y

[Wait 60 seconds]
SESSION RESET

ORCHESTRATOR: [Check again]
USAGE BUDGET MGR: Session 0%, Weekly 40%. Green. Resume work.

ORCHESTRATOR → ENGINEER: [Delegate first pending task]
```

---

## Real-Time vs. Batch

| Mode | Frequency | Latency | Best For |
|------|-----------|---------|----------|
| **Real-time** | Every 15-30 min | <1 min | Active sessions, prevent overruns |
| **Batch (EOD)** | Once at day-end | Hours | Weekly retrospectives, trend analysis |
| **On-demand** | User asks | <1 min | "Are we OK?" checks |

This skill supports real-time mode (integrated with Orchestrator).

---

## Future Extensions

1. **Per-role budgets** — Allocate separate budgets to Engineer, Senior, Opus roles
2. **Per-task budgets** — "This planning task should cost <2K tokens"
3. **Cost tracking** — Convert tokens to $USD for business metrics
4. **Trend analysis** — "You're 20% over budget this week vs. historical average"
5. **Predictive alerts** — "At current pace, weekly budget exhausted by Friday"

---

## See Also

- `operations/TOKENADVISOR.md` — Historical analysis & optimization patterns
- `config/MODEL_ASSIGNMENTS_LOCKED.md` — Saved defaults (not modified by Budget Manager)
- `operations/METRICS.md` — Token metrics collection (future: integrate with Usage Budget Manager)
