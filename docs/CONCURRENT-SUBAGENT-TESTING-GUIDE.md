# Concurrent Subagent Testing Guide

## Quick Facts

✅ **Proven Maximum:** 36 concurrent agents from single parent
✅ **Proven Depth:** 4 tiers
✅ **Proven Agent Types in Parallel:** 7 different types
✅ **Proven Largest Spawn:** 17 engineers + 10 lead-engineers + 4 senior-engineers + 2 quality-engineers + 1 security-engineer + 1 orchestrator + 1 explore

---

## Test 1: Spawn 50 Concurrent Agents

**Objective:** Find the limit beyond 36

```bash
# Create a task that spawns 50 subagents
opencode run "
Create 50 parallel subagents for comprehensive testing:
- 20 engineers
- 15 lead-engineers
- 10 senior-engineers
- 3 quality-engineers
- 1 security-engineer
- 1 principal-engineer
"

# In another terminal, monitor
watch -n 5 'opencode-tokens --session <your-session-id>'

# Check results
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id = '<your-session-id>' 
GROUP BY parent_id;
"
```

**Expected Outcome:**
- If successful: You can spawn 50+ agents
- If fails: You'll hit a limit and see error message
- Token usage: ~1M tokens (estimate)

---

## Test 2: Spawn 100 Concurrent Agents

**Objective:** Test extreme concurrency

```bash
# Create a task that spawns 100 subagents
opencode run "
Create 100 parallel subagents for extreme concurrency testing:
- 30 engineers
- 25 lead-engineers
- 20 senior-engineers
- 10 principal-engineers
- 5 quality-engineers
- 5 security-engineers
- 3 orchestrators
- 2 explores
"

# Monitor
watch -n 5 'opencode-tokens --session <your-session-id>'

# Check results
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id = '<your-session-id>' 
GROUP BY parent_id;
"
```

**Expected Outcome:**
- If successful: You can spawn 100+ agents
- If fails: You'll hit a limit
- Token usage: ~2M tokens (estimate)

---

## Test 3: Spawn 5+ Tiers Deep

**Objective:** Test nesting depth

```bash
# Create a deeply nested structure
opencode run "
Create a 5-tier deep delegation structure:

Tier 1 (Orchestrator): Create task for Tier 2
  Tier 2 (Engineer): Create task for Tier 3
    Tier 3 (Senior Engineer): Create task for Tier 4
      Tier 4 (Lead Engineer): Create task for Tier 5
        Tier 5 (Principal Engineer): Create task for Tier 6
          Tier 6 (Quality Engineer): Test if this works
"

# Check depth
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

**Expected Outcome:**
- If max_depth = 5: Tier 6 failed (depth limit)
- If max_depth = 6: You can go deeper than 4
- If max_depth = 7+: No depth limit observed

---

## Test 4: All 10 Agent Types in Parallel

**Objective:** Test agent type diversity

```bash
# Create a task that spawns one of each agent type
opencode run "
Create parallel subagents of all types:
- 1 orchestrator
- 1 engineer
- 1 lead-engineer
- 1 senior-engineer
- 1 principal-engineer
- 1 quality-engineer
- 1 security-engineer
- 1 explore
- 1 build
- 1 general
"

# Verify all types spawned
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT agent, COUNT(*) 
FROM session 
WHERE parent_id = '<your-session-id>' 
GROUP BY agent;
"
```

**Expected Outcome:**
- If all 10 types appear: Full diversity works
- If some missing: Those types can't be spawned from this parent
- Token usage: ~200k tokens (estimate)

---

## Test 5: Multiple Instances of Same Type

**Objective:** Verify you can spawn many of the same agent type

```bash
# Create a task that spawns 20 engineers
opencode run "
Create 20 parallel engineers for implementation testing
"

# Verify count
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT agent, COUNT(*) 
FROM session 
WHERE parent_id = '<your-session-id>' AND agent = 'engineer';
"
```

**Expected Outcome:**
- If count = 20: You can spawn 20 of the same type
- If count < 20: You hit a per-type limit
- Token usage: ~400k tokens (estimate)

---

## Test 6: Wide vs Deep Comparison

**Objective:** Compare concurrency strategies

### Strategy A: Wide (Many children, shallow)

```bash
opencode run "
Create 50 parallel agents (wide strategy):
- All at Tier 2
- Single parent (Orchestrator)
- Diverse agent types
"

# Measure
time opencode-tokens --session <your-session-id>
```

### Strategy B: Deep (Few children, many tiers)

```bash
opencode run "
Create deep delegation (deep strategy):
- 2 agents per tier
- 5+ tiers deep
- Sequential nesting
"

# Measure
time opencode-tokens --session <your-session-id>
```

**Compare:**
- Which completes faster?
- Which uses more tokens?
- Which is more reliable?

---

## Test 7: Stress Test - Maximum Everything

**Objective:** Find the absolute limit

```bash
# Create maximum concurrency with maximum depth
opencode run "
Stress test: Maximum concurrency and depth
- Spawn 50 agents at Tier 2
- Each spawns 10 agents at Tier 3
- Each spawns 5 agents at Tier 4
- Total: 2,500 agents across 4 tiers
"

# Monitor
watch -n 5 'opencode-tokens --session <your-session-id>'

# Check results
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT 
  COUNT(*) as total_sessions,
  COUNT(DISTINCT parent_id) as unique_parents,
  MAX(depth) as max_depth
FROM (
  WITH RECURSIVE depth_calc AS (
    SELECT id, parent_id, 1 as depth FROM session WHERE parent_id IS NULL
    UNION ALL
    SELECT s.id, s.parent_id, d.depth + 1 FROM session s
    INNER JOIN depth_calc d ON s.parent_id = d.id
  )
  SELECT * FROM depth_calc
);
"
```

**Expected Outcome:**
- Likely to hit a limit somewhere
- Will reveal the actual maximum
- Token usage: Could be 5M+ tokens

---

## Monitoring During Tests

### Real-Time Token Tracking

```bash
# Terminal 1: Start test
opencode run "Create 50 parallel agents..."

# Terminal 2: Monitor tokens
watch -n 5 'opencode-tokens --session <your-session-id>'

# Terminal 3: Monitor budget
watch -n 5 'opencode-budget --session <your-session-id>'

# Terminal 4: Monitor subagents
watch -n 5 'opencode-subagents --session <your-session-id>'
```

### Database Monitoring

```bash
# Check concurrency in real-time
watch -n 5 'sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id IS NOT NULL 
GROUP BY parent_id 
ORDER BY children DESC LIMIT 5;
"'
```

---

## Expected Results Summary

| Test | Hypothesis | Proven | Next Step |
|------|-----------|--------|-----------|
| 50 agents | Should work | ❓ | Run test |
| 100 agents | Might work | ❓ | Run test |
| 5+ tiers | Might work | ❓ | Run test |
| All 10 types | Should work | ❓ | Run test |
| 20 same type | Should work | ✅ (17 engineers) | Run test with 20+ |
| 2,500 total | Probably fails | ❓ | Run test |

---

## Failure Scenarios

### If Test Fails

**Symptom:** Agents don't spawn

```bash
# Check error in database
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT id, title, agent FROM session 
WHERE time_created > datetime('now', '-1 hour') 
ORDER BY time_created DESC;
"

# Check if parent exists
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT id, agent FROM session WHERE id = '<parent-id>';
"
```

**Possible Causes:**
1. Parent session doesn't exist
2. Hit a hard limit (queue-management skill)
3. Token budget exhausted
4. Rate limit exceeded (100 tasks/hour)
5. Network/API issue

### If Test Hangs

```bash
# Check for stuck sessions
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT id, agent, time_updated 
FROM session 
WHERE time_updated < datetime('now', '-5 minutes') 
ORDER BY time_updated DESC;
"

# Kill stuck session (if needed)
# (depends on OpenCode implementation)
```

---

## Data Collection

### After Each Test, Record:

```bash
# 1. Concurrency achieved
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id = '<test-parent-id>' 
GROUP BY parent_id;
"

# 2. Token usage
opencode-tokens --session <test-parent-id>

# 3. Depth achieved
sqlite3 ~/.local/share/opencode/opencode.db "
WITH RECURSIVE depth_calc AS (
  SELECT id, parent_id, 1 as depth FROM session WHERE id = '<test-parent-id>'
  UNION ALL
  SELECT s.id, s.parent_id, d.depth + 1 FROM session s
  INNER JOIN depth_calc d ON s.parent_id = d.id
)
SELECT MAX(depth) as max_depth FROM depth_calc;
"

# 4. Agent type distribution
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT agent, COUNT(*) 
FROM session 
WHERE parent_id = '<test-parent-id>' 
GROUP BY agent;
"

# 5. Execution time
# (measure from start to completion)
```

---

## Test Schedule

**Week 1:**
- [ ] Test 1: 50 concurrent agents
- [ ] Test 4: All 10 agent types
- [ ] Test 5: 20 same agent type

**Week 2:**
- [ ] Test 2: 100 concurrent agents
- [ ] Test 3: 5+ tiers deep
- [ ] Test 6: Wide vs Deep comparison

**Week 3:**
- [ ] Test 7: Stress test (2,500 agents)
- [ ] Analyze results
- [ ] Document findings

---

## Success Criteria

✅ **Test Passes If:**
- Agents spawn successfully
- Token usage is tracked
- No errors in database
- Execution completes

❌ **Test Fails If:**
- Agents don't spawn
- Errors in logs
- Database corruption
- Timeout/hang

---

## Next Steps

1. **Run Test 1** (50 agents) this week
2. **Document results** in this guide
3. **Run Test 2** (100 agents) next week
4. **Update MAX-CONCURRENT-SUBAGENTS.md** with findings
5. **Adjust strategy** based on actual limits

---

**Status:** Ready to test
**Last Updated:** 2026-05-16
**Data Source:** Production analysis + testing guide
