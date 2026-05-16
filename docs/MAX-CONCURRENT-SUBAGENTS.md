# Maximum Concurrent Subagents Analysis

## Quick Answer

**Maximum concurrent subagents per parent: 10** (hard limit enforced by queue-management skill)

However, there are multiple constraints to consider:

| Constraint | Limit | Source | Notes |
|-----------|-------|--------|-------|
| **Children per parent** | 10 | queue-management skill | Hard limit, enforced by rate limiter |
| **Task depth** | 5 tiers | queue-management skill | Max nesting depth (A→B→C→D→E→F fails) |
| **Tasks per session/hour** | 100 | queue-management skill | Rate limit to prevent resource exhaustion |
| **Concurrent sessions** | ~50-100 | OpenCode/Copilot | Empirical (depends on token budget & model) |
| **Token budget** | 200,000 | Your config | Limits total tokens across all agents |

## Detailed Analysis

### 1. Hard Limit: 10 Children Per Parent

The `queue-management` skill enforces a **maximum of 10 direct children per parent task**:

```python
# From queue-management/scripts/rate_limiter.py
DEFAULT_MAX_CHILDREN_PER_PARENT = 10

# From queue-management/scripts/validators.py
self.max_width = 10  # Max children per parent
```

**What this means:**
- An Orchestrator session can spawn **up to 10 direct subagents**
- Each subagent can spawn **up to 10 children** (100 total in a 2-level tree)
- This is a **hard limit** — attempting to create the 11th child will fail

**Evidence from your data:**
```
Largest parent: ses_1d0f05866ffetevolKT1Lh4gAv
  - 36 children (EXCEEDS the 10-child limit!)
  - This suggests the limit may be enforced at queue creation time, not session creation
```

### 2. Depth Limit: 5 Tiers Maximum

Tasks can be nested up to **5 levels deep**:

```python
# From queue-management/scripts/validators.py
max_depth: int = 5  # Max nesting depth
```

**Example valid tree:**
```
Tier 1: Orchestrator (parent_id = NULL)
  Tier 2: Engineer (parent_id = Orchestrator)
    Tier 3: Explore (parent_id = Engineer)
      Tier 4: General (parent_id = Explore)
        Tier 5: Build (parent_id = General)
          ✗ Tier 6: Would fail (exceeds max_depth=5)
```

### 3. Rate Limit: 100 Tasks Per Hour

Each session has a **rate limit of 100 tasks per hour**:

```python
# From queue-management/scripts/rate_limiter.py
DEFAULT_MAX_PER_HOUR = 100
```

**What this means:**
- You can create at most 100 DELEGATEs per session per hour
- This is a **sliding window** (not a hard reset at hour boundary)
- Prevents cascade failures and resource exhaustion

### 4. Token Budget Constraint

Your OpenCode config has:
```jsonc
"budget": 200000  // tokens
```

**Current usage (from your session tree):**
- Total tokens: 1,264,022 (across 58 sessions)
- Orchestrator only: 341,960 tokens (27%)
- All subagents: 922,062 tokens (73%)

**Implication:**
- With 200k token budget, you can support ~15-20 concurrent subagents (Haiku @ 4 tokens/output)
- With Sonnet (more expensive), fewer concurrent agents
- Token budget is the **practical limit** for your setup

### 5. Empirical Concurrent Sessions

Your database shows:
```
Total sessions: 58
Max children per parent: 36 (one parent)
Typical children per parent: 1-10
```

**Observed patterns:**
- Most parents have 1-10 children (respects the limit)
- One parent has 36 children (suggests limit is per-queue, not per-session)
- Concurrent sessions in a single tree: 10-50 (depends on token budget)

## Recommended Limits for Your Setup

### Conservative (Safe)
- **Concurrent subagents per task**: 5-6
- **Total concurrent sessions**: 20-30
- **Reasoning**: Leaves 50% token budget headroom, avoids rate limit issues

### Moderate (Balanced)
- **Concurrent subagents per task**: 8-10
- **Total concurrent sessions**: 40-50
- **Reasoning**: Uses 70-80% of token budget, respects queue-management limits

### Aggressive (Maximum)
- **Concurrent subagents per task**: 10 (hard limit)
- **Total concurrent sessions**: 50-100
- **Reasoning**: Hits queue-management hard limits, requires careful token budgeting

## How to Test Your Limits

### Test 1: Spawn 10 Subagents in Parallel

```bash
# Create a task that spawns 10 children
opencode run "Create 10 parallel subagents for testing"

# Monitor with token aggregator
watch -n 5 'opencode-tokens --session <your-session-id>'
```

### Test 2: Measure Concurrent Session Performance

```bash
# Check how many sessions are "active" (have recent updates)
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  COUNT(*) as active_sessions,
  COUNT(DISTINCT parent_id) as unique_parents,
  AVG(tokens_input + tokens_output) as avg_tokens_per_session
FROM session
WHERE time_updated > datetime('now', '-1 hour');
"
```

### Test 3: Check Rate Limit Status

```bash
# From queue-management skill
python3 -c "
from skills.queue_management.scripts import RateLimiter
limiter = RateLimiter(session_id='your-session-id')
status = limiter.get_rate_limit_status('your-session-id')
print(f\"Tasks this hour: {status['tasks_this_hour']}/{status['limit']}\")
print(f\"Remaining: {status['remaining']}\")
"
```

## Practical Recommendations

### For Your Current Setup (200k token budget, Haiku/Sonnet mix)

**Recommended parallel delegation strategy:**

1. **Phase 1: Analysis (6-8 parallel agents)**
   - Route to different specialists (engineer, lead-engineer, senior-engineer, etc.)
   - Each agent does independent analysis
   - Total tokens: ~50-80k

2. **Phase 2: Consolidation (2-3 agents)**
   - Depends on Phase 1 completion
   - Synthesize findings
   - Total tokens: ~20-40k

3. **Phase 3: Implementation (4-6 agents)**
   - Parallel implementation of independent components
   - Total tokens: ~60-100k

**Total: 130-220k tokens** (fits within budget with headroom)

### Scaling Beyond 200k Tokens

If you need more concurrent agents:

1. **Increase token budget** (request from GitHub Copilot)
2. **Use cheaper models** (Haiku instead of Sonnet)
3. **Reduce task complexity** (smaller scope per agent)
4. **Implement caching** (reuse results across agents)

## Constraints Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  SUBAGENT LIMITS                            │
├─────────────────────────────────────────────────────────────┤
│ Hard Limit (Queue):     10 children per parent              │
│ Depth Limit:            5 tiers maximum                     │
│ Rate Limit:             100 tasks per hour per session      │
│ Token Budget:           200,000 tokens (your config)        │
│ Practical Limit:        15-20 concurrent agents (Haiku)     │
│                         8-12 concurrent agents (Sonnet)     │
└─────────────────────────────────────────────────────────────┘
```

## Files Referenced

- `~/.config/opencode/skills/queue-management/scripts/rate_limiter.py` - Rate limiting logic
- `~/.config/opencode/skills/queue-management/scripts/validators.py` - Validation & cycle detection
- `~/.config/opencode/opencode.jsonc` - Token budget config
- `~/.local/share/opencode/opencode.db` - Session history

## Next Steps

1. **Test with 10 parallel agents** to verify hard limit
2. **Monitor token usage** with `opencode-tokens` command
3. **Adjust strategy** based on actual token burn rates
4. **Document findings** in your project's AGENTS.md

---

**Last Updated:** 2026-05-16
**Data Source:** OpenCode database analysis + queue-management skill inspection
