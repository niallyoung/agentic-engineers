# Quick Start: Token Visibility

**Time to complete:** 5 minutes  
**Prerequisite:** OpenCode harness installed (`make install-opencode`)

---

## Overview

Token visibility gives you real-time insight into how tokens are consumed across all agents and subagents in a session. This is critical because:

- **Orchestrator sees only ~27%** of actual token usage
- **Subagents account for ~73%** of usage
- Without visibility, you can exceed budgets unexpectedly

---

## Step 1: Find Your Session ID

```bash
# OpenCode stores sessions in SQLite
sqlite3 ~/.local/share/opencode/opencode.db "SELECT id, created_at FROM session ORDER BY created_at DESC LIMIT 5;"
```

Or check the OpenCode TUI — the session ID is shown in the status bar.

---

## Step 2: Check Real-Time Token Usage

```bash
# Usage by agent (current session)
opencode-tokens --session <session-id>

# Example output:
# Session: abc123
# ─────────────────────────────────────────
# orchestrator          12,450 tokens  (9%)
# engineer-task-001     89,230 tokens  (65%)
# quality-engineer-001  31,100 tokens  (23%)
# senior-engineer-001    4,220 tokens  (3%)
# ─────────────────────────────────────────
# TOTAL                137,000 tokens
```

---

## Step 3: Watch Usage in Real Time

```bash
# Updates every 5 seconds
watch -n 5 'opencode-tokens --session <session-id>'
```

---

## Step 4: Query the Database Directly

```bash
# How many subagents are running?
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id IS NOT NULL 
GROUP BY parent_id 
ORDER BY children DESC;
"

# What is the deepest nesting level?
sqlite3 ~/.local/share/opencode/opencode.db "
WITH RECURSIVE depth_calc AS (
  SELECT id, parent_id, 1 as depth FROM session WHERE parent_id IS NULL
  UNION ALL
  SELECT s.id, s.parent_id, d.depth + 1 FROM session s
  INNER JOIN depth_calc d ON s.parent_id = d.id
)
SELECT MAX(depth) as max_depth FROM depth_calc;
"

# Total tokens across all sessions today
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT SUM(tokens_in + tokens_out) as total_tokens
FROM session
WHERE date(created_at) = date('now');
"
```

---

## Recommended Token Allocation

For a typical session with a 200k token budget:

| Role | Tokens | % |
|------|--------|---|
| Orchestrator (Haiku, low) | 60k | 30% |
| Engineer (Haiku, high) | 80k | 40% |
| Quality Engineer (Sonnet, medium) | 30k | 15% |
| Senior Engineer (Sonnet, high) | 20k | 10% |
| Other roles | 10k | 5% |
| **Total** | **200k** | **100%** |

Adjust based on:
- Task complexity (complex tasks need more tokens)
- Parallel delegation (more agents = higher concurrent usage, same total)
- Model selection (Opus uses significantly more than Haiku)

---

## Parallel Delegation Impact

Parallel delegation **reduces wall-clock time** but increases concurrent token usage:

| Approach | Wall-clock | Peak tokens | Total tokens |
|----------|-----------|-------------|--------------|
| Sequential (3 tasks) | 3 hours | 2,000 | 6,000 |
| Parallel (3 tasks) | 1 hour | 6,000 | 6,000 |

**Benefit:** 2 hours saved with the same total token cost.

---

## Related Documentation

- [docs/QUICK-START-BUDGET-CHECKING.md](QUICK-START-BUDGET-CHECKING.md) — Set and enforce token budgets
- [docs/TOKEN-COST-MONITORING.md](TOKEN-COST-MONITORING.md) — Full monitoring reference
- [docs/TOKEN-USAGE-TRACKING.md](TOKEN-USAGE-TRACKING.md) — Token accounting details
- [docs/CONCURRENT-SUBAGENT-CAPACITY.md](CONCURRENT-SUBAGENT-CAPACITY.md) — Subagent capacity analysis
