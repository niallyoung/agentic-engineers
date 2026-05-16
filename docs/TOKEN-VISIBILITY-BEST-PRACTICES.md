# Token Visibility & Monitoring Best Practices

Real-time token tracking for all agents and subagents. Enables cost optimization, budget management, and capacity planning.

---

## Quick Start

### Get Your Session ID
```bash
SESSION_ID=$(sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session ORDER BY time_created DESC LIMIT 1;")
echo $SESSION_ID
```

### Monitor Tokens in Real-Time
```bash
# Updates every 5 seconds
watch -n 5 "opencode-tokens --session $SESSION_ID"
```

### Check Budget
```bash
opencode-budget --session $SESSION_ID --limit 200000
```

### List Subagents
```bash
opencode-subagents --session $SESSION_ID
```

---

## Three CLI Commands

### 1. opencode-tokens

**Purpose:** Real-time token usage by agent and role

**Usage:**
```bash
opencode-tokens --session <session-id>
opencode-tokens --session <session-id> --format json
opencode-tokens --session <session-id> --format csv
```

**Output:**
```
Session: ses_1d0f05866ffetevolKT1Lh4gAv
Total tokens: 708,198

By Agent Type:
  engineer:        342,156 (48.3%)
  lead-engineer:   198,042 (28.0%)
  senior-engineer: 112,000 (15.8%)
  quality-engineer: 56,000 (7.9%)

By Effort Level:
  high:   450,000 (63.5%)
  medium: 200,000 (28.2%)
  low:     58,198 (8.2%)

Peak Concurrent: 17 agents
Duration: 2h 34m
```

### 2. opencode-budget

**Purpose:** Track token budget consumption

**Usage:**
```bash
opencode-budget --session <session-id> --limit 200000
opencode-budget --session <session-id> --limit 200000 --format json
```

**Output:**
```
Session: ses_1d0f05866ffetevolKT1Lh4gAv
Budget: 200,000 tokens
Used: 708,198 tokens (354% of budget)
Remaining: -508,198 tokens (OVER BUDGET)

Breakdown:
  Orchestrator:    60,000 (30%)
  Engineer:       150,000 (75%)
  Quality Engineer: 30,000 (15%)
  Senior Engineer:  20,000 (10%)
  Other:            8,198 (4%)

Status: ⚠️  OVER BUDGET by 508,198 tokens
```

### 3. opencode-subagents

**Purpose:** List all subagents in session

**Usage:**
```bash
opencode-subagents --session <session-id>
opencode-subagents --session <session-id> --format json
```

**Output:**
```
Session: ses_1d0f05866ffetevolKT1Lh4gAv
Total subagents: 36

Tier 1 (Parent):
  ses_1d0f05866ffetevolKT1Lh4gAv (orchestrator, 708k tokens)

Tier 2 (Children):
  ses_2a1f06867ffetevolKT1Lh4gAv (engineer, 342k tokens)
  ses_2b2f06868ffetevolKT1Lh4gAv (lead-engineer, 198k tokens)
  ses_2c3f06869ffetevolKT1Lh4gAv (senior-engineer, 112k tokens)
  ... (33 more)

Tier 3 (Grandchildren):
  ses_3a1f06870ffetevolKT1Lh4gAv (quality-engineer, 56k tokens)
  ... (8 more)

Tier 4 (Great-grandchildren):
  ses_4a1f06871ffetevolKT1Lh4gAv (explore, 12k tokens)
  ... (2 more)
```

---

## Monitoring Strategies

### Strategy 1: Real-Time Monitoring During Active Work

**When:** Long-running tasks (>30 minutes)

**How:**
```bash
# Terminal 1: Run your task
opencode run "Create 10 parallel agents for analysis"

# Terminal 2: Monitor tokens
SESSION_ID=$(sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session ORDER BY time_created DESC LIMIT 1;")
watch -n 5 "opencode-tokens --session $SESSION_ID"
```

**What to watch for:**
- Token growth rate (should be steady, not spiking)
- Concurrent agent count (should match expected parallelism)
- Peak tokens (should not exceed budget)

### Strategy 2: Budget Tracking

**When:** Cost-sensitive work or limited budgets

**How:**
```bash
# Set a budget limit
BUDGET=200000

# Check status before starting
opencode-budget --session $SESSION_ID --limit $BUDGET

# Monitor during work
watch -n 30 "opencode-budget --session $SESSION_ID --limit $BUDGET"

# Alert if approaching limit
if [ $(opencode-budget --session $SESSION_ID --limit $BUDGET | grep "Remaining" | awk '{print $NF}') -lt 10000 ]; then
  echo "WARNING: Less than 10k tokens remaining"
fi
```

### Strategy 3: Subagent Capacity Planning

**When:** Planning parallel delegation

**How:**
```bash
# Check current subagent count
opencode-subagents --session $SESSION_ID

# Estimate tokens for new agents
# Rule of thumb: 20k tokens per agent (varies by task)
AGENTS=10
TOKENS_PER_AGENT=20000
ESTIMATED_TOTAL=$((AGENTS * TOKENS_PER_AGENT))

# Check if budget allows
REMAINING=$(opencode-budget --session $SESSION_ID --limit 200000 | grep "Remaining" | awk '{print $NF}')
if [ $REMAINING -gt $ESTIMATED_TOTAL ]; then
  echo "✅ Budget allows $AGENTS agents"
else
  echo "❌ Budget insufficient for $AGENTS agents"
fi
```

### Strategy 4: Post-Execution Analysis

**When:** After task completion

**How:**
```bash
# Export metrics for analysis
opencode-tokens --session $SESSION_ID --format json > metrics.json

# Analyze by agent type
jq '.by_agent_type' metrics.json

# Analyze by effort level
jq '.by_effort_level' metrics.json

# Calculate cost per agent
jq '.total_tokens / .agent_count' metrics.json
```

---

## Database Queries

### How Many Agents Are Running?

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children, SUM(tokens_used) as total_tokens
FROM session 
WHERE parent_id IS NOT NULL 
GROUP BY parent_id 
ORDER BY children DESC;
"
```

**Output:**
```
parent_id|children|total_tokens
ses_1d0f05866ffetevolKT1Lh4gAv|36|708198
ses_2a1f06867ffetevolKT1Lh4gAv|5|125000
ses_2b2f06868ffetevolKT1Lh4gAv|3|87000
```

### What's the Deepest Nesting?

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
WITH RECURSIVE depth_calc AS (
  SELECT id, parent_id, 1 as depth FROM session WHERE parent_id IS NULL
  UNION ALL
  SELECT s.id, s.parent_id, d.depth + 1 FROM session s
  INNER JOIN depth_calc d ON s.parent_id = d.id
)
SELECT MAX(depth) as max_depth FROM depth_calc;
"
```

**Output:**
```
max_depth
4
```

### Which Agent Types Are Running?

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT agent, COUNT(*) as count, SUM(tokens_used) as total_tokens
FROM session 
WHERE parent_id = 'ses_1d0f05866ffetevolKT1Lh4gAv'
GROUP BY agent
ORDER BY total_tokens DESC;
"
```

**Output:**
```
agent|count|total_tokens
engineer|17|342156
lead-engineer|10|198042
senior-engineer|4|112000
quality-engineer|2|56000
security-engineer|1|0
orchestrator|1|0
explore|1|0
```

### Token Usage Over Time

```bash
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  strftime('%Y-%m-%d %H:%M', time_created) as minute,
  COUNT(*) as sessions,
  SUM(tokens_used) as tokens
FROM session
WHERE parent_id IS NOT NULL
GROUP BY minute
ORDER BY minute;
"
```

**Output:**
```
minute|sessions|tokens
2026-05-16 14:00|3|45000
2026-05-16 14:01|5|67000
2026-05-16 14:02|8|98000
2026-05-16 14:03|12|145000
```

---

## Token Allocation Guidelines

### By Role

| Role | Typical Tokens | % of Budget | Notes |
|------|----------------|-------------|-------|
| Orchestrator (Haiku, low) | 60k | 30% | Routing, coordination, metrics |
| Engineer (Haiku, high) | 80k | 40% | Implementation, well-scoped tasks |
| Quality Engineer (Sonnet, medium) | 30k | 15% | Verification, feedback |
| Senior Engineer (Sonnet, high) | 20k | 10% | Complex tasks, planning |
| Lead Engineer (Sonnet, high) | 5k | 2.5% | Code review, guidance |
| Principal Engineer (Opus, high) | 3k | 1.5% | Architecture, escalations |
| Security Engineer (Opus, max) | 2k | 1% | Security analysis |
| Model Engineer (Sonnet, high) | 0 | 0% | Runs post-task, not in budget |

**Total:** 200k tokens (typical session)

### By Task Complexity

| Complexity | Tokens | Examples |
|-----------|--------|----------|
| Trivial | 5k-10k | Lint fixes, typos, simple PRs |
| Simple | 10k-20k | Bug fixes with clear root cause |
| Medium | 20k-40k | Feature implementation, security fixes |
| Complex | 40k-80k | Architecture changes, CI failures |
| Very Complex | 80k-150k | Major refactors, threat modeling |
| Parallel (3 agents) | 60k | 3 × 20k agents running concurrently |
| Parallel (10 agents) | 200k | 10 × 20k agents running concurrently |

### By Model

| Model | Tokens per Task | Cost | Use When |
|-------|-----------------|------|----------|
| Haiku (low) | 5k-10k | $0.03 | Routing, simple tasks |
| Haiku (high) | 15k-25k | $0.03 | Implementation, well-scoped |
| Sonnet (medium) | 20k-30k | $0.09 | Verification, medium complexity |
| Sonnet (high) | 30k-50k | $0.09 | Complex tasks, planning |
| Opus 4.6 (high) | 40k-80k | $0.15 | Architecture, design |
| Opus 4.7 (max) | 60k-120k | $0.15 | Security, threat modeling |

---

## Cost Optimization

### Reduce Token Usage

1. **Better scoping:** Smaller, well-defined tasks use fewer tokens
2. **Pre-written plans:** Agents don't need to explore; they execute
3. **Reuse context:** Share findings across related tasks
4. **Parallel delegation:** Same total tokens, but faster wall-clock
5. **Right model:** Use Haiku for simple tasks, Opus only for complex

### Monitor Cost Trends

```bash
# Daily cost summary
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  DATE(time_created) as date,
  COUNT(*) as tasks,
  SUM(tokens_used) as total_tokens,
  ROUND(SUM(tokens_used) * 0.00003, 2) as cost_haiku,
  ROUND(SUM(tokens_used) * 0.00009, 2) as cost_sonnet,
  ROUND(SUM(tokens_used) * 0.00015, 2) as cost_opus
FROM session
WHERE parent_id IS NULL
GROUP BY date
ORDER BY date DESC;
"
```

### Budget Alerts

```bash
# Alert if any session exceeds 100k tokens
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT id, tokens_used, agent
FROM session
WHERE tokens_used > 100000
ORDER BY tokens_used DESC;
"
```

---

## Troubleshooting

### Q: opencode-tokens command not found

**A:** Install the token aggregator plugin:
```bash
# Plugin should be at ~/.config/opencode/.opencode/plugins/token-aggregator.sh
# Symlinks should be at /usr/local/bin/opencode-tokens, etc.

# Verify installation
ls -la ~/.config/opencode/.opencode/plugins/token-aggregator.sh
ls -la /usr/local/bin/opencode-tokens

# If missing, reinstall
make install
```

### Q: Session ID not found

**A:** Get the correct session ID:
```bash
# List all sessions
sqlite3 ~/.local/share/opencode/opencode.db "SELECT id FROM session LIMIT 10;"

# Get most recent session
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session ORDER BY time_created DESC LIMIT 1;"
```

### Q: Budget shows negative remaining tokens

**A:** You've exceeded your budget. Options:
1. Set a higher limit: `opencode-budget --session <id> --limit 500000`
2. Analyze what used tokens: `opencode-tokens --session <id>`
3. Escalate to Principal Engineer for approval to continue

### Q: Token counts seem wrong

**A:** Verify with database query:
```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT tokens_used FROM session WHERE id = '<session-id>';"
```

If database shows different value, the plugin cache may be stale. Restart the plugin:
```bash
pkill -f token-aggregator
sleep 2
opencode-tokens --session <session-id>
```

---

## Integration with Workflow

### In DELEGATE Block

Orchestrator should note token budget:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-16-feature-implementation
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Implement feature X in service Y
context:
  - Budget: 50k tokens available
  - Current usage: 120k of 200k total
  - Estimate: 30k tokens for this task
plan:
  1. ...
---
```

### In HANDBACK Block

Agent should report actual token usage:

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-16-feature-implementation
status: complete
deliverables:
  - ...
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4-5
effort: high
duration_minutes: 18
---
```

### In Orchestrator Routing

Orchestrator should check budget before delegating:

```bash
# Pseudo-code
SESSION_ID=$(get_current_session)
REMAINING=$(opencode-budget --session $SESSION_ID --limit 200000 | grep Remaining)

if [ $REMAINING -lt 50000 ]; then
  # Not enough budget for next task
  escalate_to_principal_engineer()
else
  # Proceed with delegation
  create_delegate()
fi
```

---

## Documentation

- **Quick Start:** `docs/QUICK-START-CONCURRENT-AGENTS.md`
- **Capacity Analysis:** `docs/CONCURRENT-SUBAGENT-CAPACITY.md`
- **Testing Guide:** `docs/CONCURRENT-SUBAGENT-TESTING-GUIDE.md`
- **Plugin Details:** `~/.config/opencode/.opencode/plugins/TOKEN-AGGREGATOR.md`

---

**Status:** ✅ Ready to use
**Last Updated:** 2026-05-16
**Plugin Version:** 1.0
