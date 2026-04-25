---
name: orchestrator-workflow-checklist
description: Step-by-step Orchestrator workflow with automatic usage-tracking integration
---

# Orchestrator Workflow Checklist

Daily checklist for Orchestrator role with **automatic usage-tracking** integrated at key points.

---

## Session Initialization

- [ ] **AUTOMATIC: Capture baseline usage**
  ```bash
  bash skills/usage-tracking/scripts/capture_token_usage.sh
  ```
  Expected output: "Captured usage snapshot: Session X%, Weekly Y%, Status: GREEN/YELLOW/RED"

- [ ] Plan session (create TODO.md)
  - [ ] List all pending tasks
  - [ ] Estimate effort and scope
  - [ ] Note any budget constraints

- [ ] Review current budget status
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh analyze
  ```
  Output: Session%, weekly%, velocity, hours to reset

---

## For Each Task

### Pre-Delegation

- [ ] **AUTOMATIC: Check budget before delegating**
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json | jq '.session.current'
  ```

- [ ] Make routing decision (AGENTS.md decision tree)
  - Session ≤ 70%? → GREEN → use best model (Sonnet/Opus as needed)
  - Session 70-85%? → YELLOW → use Sonnet, estimate token budget
  - Session > 85%? → RED → use Haiku only OR defer to next session

- [ ] Create DELEGATE block with budget context
  ```yaml
  budget_context:
    session_pct_at_delegation: 65
    hours_until_reset: 4.2
    status: YELLOW
    model_recommendation: "Sonnet (efficient)"
  ```

- [ ] Mark task IN_PROGRESS in TODO

### During Task Execution

- [ ] **AUTOMATIC: Hourly checkpoint** (while waiting for HANDBACK)
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
  ```
  - Velocity: How fast is usage climbing?
  - Hours left: On track to exceed limits?
  - Trend: Rising/stable/falling?
  - Action: Continue / adjust model for next task / escalate break decision

### Task Completion

- [ ] Receive HANDBACK from agent
  - Expected fields: `usage_before_session_pct`, `usage_after_session_pct`, `tokens_consumed_estimate`
  - Expected fields: `model_used`, `efficiency_note`

- [ ] Verify metrics are included
  - [ ] Did model consumption match estimate?
  - [ ] Was efficiency reasonable for scope?
  - [ ] Any anomalies to flag (over/under consumption)?

- [ ] **Record metrics** (metrics-collection.md)
  - Include usage data from HANDBACK
  - Track: tokens consumed, velocity, efficiency

- [ ] Mark task DONE in TODO with timestamp

---

## Periodic Checkpoints (Every 30 Minutes)

- [ ] **AUTOMATIC: Usage status check**
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
  ```

- [ ] Interpret output
  - Session usage: ____%
  - Trend: RISING / FALLING / STABLE
  - Velocity: ____%/hour
  - Hours to reset: _____ hours
  - Budget status: GREEN / YELLOW / RED

- [ ] Make decisions for next task
  - [ ] GREEN → Continue normal (Sonnet for complex work)
  - [ ] YELLOW → Use Sonnet (efficient), be mindful of budget
  - [ ] RED → Haiku only OR consider break until reset

- [ ] Update TODO checkpoint log
  ```
  # Checkpoint 14:30 — Session 65% (rising 5.2%/hr), 4.8h to reset
  - Delegated: feature X to Engineer
  - Next: Continue with refactor task
  - Budget: YELLOW, monitoring closely
  ```

---

## End of Session

- [ ] **AUTOMATIC: Final usage snapshot**
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh analyze
  ```
  Output: Full session metrics, trend analysis, velocity

- [ ] Record final metrics
  - [ ] Total tokens consumed in session
  - [ ] Average velocity (tokens per hour)
  - [ ] Peak usage point
  - [ ] Notes on patterns or anomalies

- [ ] Export usage data
  ```bash
  bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json > ~/session-usage-2026-04-25.json
  ```

---

## Daily Analysis (17:00 or session end)

- [ ] Run tokenadvisor analysis
  ```bash
  bash monitoring/tokenadvisor-scheduler.md
  ```

- [ ] **Usage patterns**: Review from usage-tracking data
  - Which tasks consumed most tokens?
  - Were expensive tasks justified by complexity?
  - Any efficiency anomalies?

- [ ] Coordinate with Model Engineer
  - [ ] Confirm model routing was optimal
  - [ ] Flag any model mismatches
  - [ ] Recommend changes for similar future tasks

- [ ] Apply recommendations to tomorrow's planning
  - [ ] Update AGENTS.md routing if needed
  - [ ] Adjust effort/model assignments for similar tasks
  - [ ] Note any patterns to watch

---

## Budget-Aware Delegation Template

Use this template when creating DELEGATE blocks:

```yaml
---
handoff_type: DELEGATE
task_id: YYYY-MM-DD-task-name
role: [Engineer | Senior Engineer | Lead Engineer | Principal Engineer | Security Engineer]
model: [haiku | sonnet | opus]
effort: low | medium | high | max
budget_context:
  session_pct_at_delegation: XX
  estimated_tokens_needed: XXXX
  hours_until_reset: X.X
  status: GREEN | YELLOW | RED
  recommendation: "Haiku suitable (routine) / Sonnet sufficient (balanced) / Opus needed (complex)"
scope: >
  ...
context:
  ...
success_criteria:
  ...
plan:
  ...
---
```

Agent will see budget status upfront and can:
- Optimize implementation to stay within estimate
- Ask for clarification if estimate seems off
- Escalate if approaching limit before completion

---

## Automatic Voice Alerts

When session usage hits thresholds:
- **70%**: "Session usage high, 70 percent" (Daniel voice, warning)
- **85%**: "Session usage critical, 85 percent" (Daniel voice, alert)

No action needed — alerts inform decisions naturally.

---

## Manual Overrides

**If voice alerts are too intrusive:**
```bash
# Run captures silently (no voice alerts)
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```

**If you need to pause tracking temporarily:**
```bash
# All commands support --silent flag
bash skills/usage-tracking/scripts/usage-tracking.sh capture --silent
```

---

## Quick Reference: Automatic Points

| When | What | Command |
|------|------|---------|
| Session start | Capture baseline | `capture_token_usage.sh` |
| Before delegation | Check budget | `usage-tracking.sh analyze --json` |
| Every 30 min | Checkpoint | `usage-tracking.sh snapshot` |
| Task completion | Verify metrics | Check HANDBACK for usage fields |
| Session end | Final metrics | `usage-tracking.sh analyze` |

---

## Troubleshooting

### "No usage data captured yet"
- First session? Run initial capture first
- `bash skills/usage-tracking/scripts/capture_token_usage.sh`

### Voice alerts not working
- Check system volume: `osascript -e 'get volume settings'`
- Or disable: `bash capture_token_usage.sh --silent`

### Usage percentages stuck at 0%
- Can't programmatically query Claude API usage
- Manual entry option: see USAGE-BUDGET-MANAGER.md

---

## See Also

- `skills/usage-tracking/SKILL.md` — Complete skill documentation
- `skills/usage-tracking/AGENT-INTEGRATION.md` — All agent usage patterns
- `HANDOFF.md` — Markup protocol (includes automatic tracking section)
- `USAGE-BUDGET-MANAGER.md` — Real-time budget checking
- `TOKEN-USAGE-TRACKING.md` — Technical setup and configuration
