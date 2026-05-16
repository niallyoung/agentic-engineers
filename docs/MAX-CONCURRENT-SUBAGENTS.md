# Concurrent Subagents & Token Usage Tracking

## Overview

This document provides **observability and tracking** for concurrent subagents and token usage. There are **no artificial constraints or limits** — you can spawn as many subagents as needed and use as many tokens as required. This guide helps you **monitor and understand** what you're actually using.

## Current Usage Patterns

Your database shows:
```
Total sessions: 58
Max children per parent: 36 (one parent)
Typical children per parent: 1-10
Total tokens used: 1,264,022 (across all sessions)
```

**Observed patterns:**
- You've successfully spawned up to 36 children from a single parent
- Typical parallel delegation uses 1-10 subagents per task
- Token usage varies widely by agent type and task complexity

## Token Usage Tracking

### Monitor Current Usage

```bash
# Show total tokens used by all agents
opencode-tokens --session <your-session-id>

# Check budget status (if you set one)
opencode-budget --session <your-session-id> --limit <your-limit>

# List all subagent sessions
opencode-subagents --session <your-session-id>
```

### Real-Time Monitoring

```bash
# Watch tokens update every 5 seconds
watch -n 5 'opencode-tokens --session <your-session-id>'

# Or budget status
watch -n 5 'opencode-budget --session <your-session-id>'
```

## Token Usage by Agent Type

From your 58 sessions:

| Agent Type | Tokens | Percentage |
|-----------|--------|-----------|
| Engineer | 422,910 | 33% |
| Orchestrator | 341,960 | 27% |
| Lead Engineer | 133,629 | 11% |
| Senior Engineer | 102,434 | 8% |
| Quality Engineer | 83,609 | 7% |
| Explore | 60,156 | 5% |
| Build | 34,244 | 3% |
| Security Engineer | 33,075 | 3% |
| General | 28,926 | 2% |
| Principal Engineer | 23,079 | 2% |

**Key insight:** Engineers use 33% of tokens, but Orchestrator only sees its own 27%. The token aggregator plugin reveals the hidden 73%.

## Scaling Subagents

You can spawn as many subagents as needed:

- **Tested:** 36 children from a single parent (successful)
- **Typical:** 6-10 parallel agents per task (common pattern)
- **Maximum:** No hard limit — scale based on your needs

### Example: Large Parallel Delegation

```bash
# Spawn 20 parallel agents for analysis
opencode run "Create 20 parallel subagents for comprehensive analysis"

# Monitor with token aggregator
watch -n 5 'opencode-tokens --session <your-session-id>'
```

## Tracking Token Usage

### Per-Session Breakdown

```bash
# Show tokens by agent type
opencode-tokens --session <your-session-id>

# Output includes:
# - Total tokens (input + output + reasoning)
# - Breakdown by agent type
# - Breakdown by model
# - Cache tokens (separate, cheaper)
```

### Historical Analysis

```bash
# Query database for historical patterns
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  agent,
  COUNT(*) as sessions,
  SUM(tokens_input + tokens_output) as total_tokens,
  AVG(tokens_input + tokens_output) as avg_tokens
FROM session
GROUP BY agent
ORDER BY total_tokens DESC;
"
```

### Cost Analysis

```bash
# Calculate cost by model
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  json_extract(model, '$.id') as model,
  COUNT(*) as sessions,
  SUM(tokens_input + tokens_output) as total_tokens,
  SUM(cost) as total_cost
FROM session
GROUP BY model
ORDER BY total_cost DESC;
"
```

## Optimization Strategies

### Monitor Token Burn Rates

```bash
# Check average tokens per agent type
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  agent,
  COUNT(*) as count,
  AVG(tokens_input + tokens_output) as avg_tokens,
  MAX(tokens_input + tokens_output) as max_tokens,
  MIN(tokens_input + tokens_output) as min_tokens
FROM session
GROUP BY agent
ORDER BY avg_tokens DESC;
"
```

### Identify Expensive Tasks

```bash
# Find sessions using most tokens
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  id,
  title,
  agent,
  tokens_input + tokens_output as total_tokens
FROM session
ORDER BY total_tokens DESC
LIMIT 20;
"
```

### Track Trends Over Time

```bash
# Tokens per day
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  date(time_created / 1000, 'unixepoch') as date,
  COUNT(*) as sessions,
  SUM(tokens_input + tokens_output) as total_tokens
FROM session
GROUP BY date
ORDER BY date DESC;
"
```

## Files for Tracking

- **Token aggregator:** `~/.config/opencode/.opencode/plugins/token-aggregator.sh`
- **Database:** `~/.local/share/opencode/opencode.db`
- **CLI commands:** `opencode-tokens`, `opencode-budget`, `opencode-subagents`

## Next Steps

1. **Use the token aggregator** in your workflow:
   ```bash
   opencode-tokens --session <your-session-id>
   ```

2. **Monitor token usage** during parallel delegation:
   ```bash
   watch -n 5 'opencode-tokens --session <your-session-id>'
   ```

3. **Analyze patterns** to understand token burn:
   ```bash
   sqlite3 ~/.local/share/opencode/opencode.db "SELECT agent, COUNT(*), AVG(tokens_input + tokens_output) FROM session GROUP BY agent;"
   ```

4. **Optimize based on data:**
   - Identify expensive agent types
   - Adjust task decomposition strategy
   - Choose models based on actual usage patterns

---

**Last Updated:** 2026-05-16
**Status:** Observability-focused, no constraints
**Data Source:** OpenCode database + token aggregator plugin
