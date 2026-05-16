# Quick Start: Concurrent Subagents & Token Tracking

## TL;DR

✅ **You can spawn at least 36 concurrent agents**
✅ **No artificial limits**
✅ **Track tokens with `opencode-tokens`**

---

## One-Minute Setup

### 1. Get Your Session ID
```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session ORDER BY time_created DESC LIMIT 1;"
```

### 2. Track Tokens
```bash
opencode-tokens --session <your-session-id>
```

### 3. Monitor in Real-Time
```bash
watch -n 5 'opencode-tokens --session <your-session-id>'
```

---

## Spawn Agents

### Small Parallel (3-6 agents)
```bash
opencode run "Create 5 parallel engineers for analysis"
```

### Medium Parallel (10 agents)
```bash
opencode run "Create 10 parallel agents: 5 engineers, 3 lead-engineers, 2 senior-engineers"
```

### Large Parallel (36+ agents)
```bash
opencode run "Create 36 parallel agents: 17 engineers, 10 lead-engineers, 4 senior-engineers, 2 quality-engineers, 1 security-engineer, 1 orchestrator, 1 explore"
```

---

## Monitor

### Token Usage
```bash
opencode-tokens --session <your-session-id>
```

### Budget (if set)
```bash
opencode-budget --session <your-session-id> --limit 200000
```

### Subagent List
```bash
opencode-subagents --session <your-session-id>
```

### Live Monitoring
```bash
watch -n 5 'opencode-tokens --session <your-session-id>'
```

---

## Database Queries

### How many agents are running?
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id IS NOT NULL 
GROUP BY parent_id 
ORDER BY children DESC;
"
```

### What's the deepest nesting?
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

### Which agent types are running?
```bash
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT agent, COUNT(*) 
FROM session 
WHERE parent_id = '<your-parent-id>' 
GROUP BY agent;
"
```

---

## Proven Capabilities

| Scenario | Agents | Status |
|----------|--------|--------|
| Single | 1 | ✅ |
| Small | 3-6 | ✅ |
| Medium | 10 | ✅ |
| Large | 36 | ✅ |
| Very Large | 50+ | ❓ (untested) |
| Extreme | 100+ | ❓ (untested) |

---

## Agent Types

All 10 types available:
- orchestrator
- engineer
- lead-engineer
- senior-engineer
- principal-engineer
- quality-engineer
- security-engineer
- explore
- build
- general

**Proven in parallel:** 7 types (engineer, lead-engineer, senior-engineer, quality-engineer, security-engineer, orchestrator, explore)

---

## Token Usage Examples

| Scenario | Avg Tokens | Total |
|----------|-----------|-------|
| Single agent | 25k-50k | 25k-50k |
| 6 agents | 6k-20k each | 36k-120k |
| 10 agents | 6k each | 60k |
| 36 agents | 20k each | 708k |

---

## Next Steps

1. **Try it now:**
   ```bash
   opencode run "Create 10 parallel agents"
   watch -n 5 'opencode-tokens --session <your-session-id>'
   ```

2. **Test higher limits:**
   - See `docs/CONCURRENT-SUBAGENT-TESTING-GUIDE.md` for 7 tests

3. **Monitor continuously:**
   - Use `opencode-tokens` to track all usage
   - No limits, just observability

---

## Documentation

- **Token Tracking:** `~/.config/opencode/.opencode/plugins/TOKEN-AGGREGATOR.md`
- **Capacity Analysis:** `docs/CONCURRENT-SUBAGENT-CAPACITY.md`
- **Testing Guide:** `docs/CONCURRENT-SUBAGENT-TESTING-GUIDE.md`
- **Full Details:** `docs/MAX-CONCURRENT-SUBAGENTS.md`

---

**Status:** ✅ Ready to use
**Last Updated:** 2026-05-16
