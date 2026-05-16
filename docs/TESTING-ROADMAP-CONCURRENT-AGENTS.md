# Testing Roadmap: Finding Concurrent Subagent Limits

**Goal:** Determine the actual limits of concurrent subagent spawning beyond the proven 36 agents.

**Current Status:** 36 agents proven in production. Actual limit unknown but likely much higher.

**Timeline:** 2-3 weeks of testing (parallel execution)

---

## Test Overview

| Test | Agents | Depth | Types | Goal | Est. Time | Est. Tokens |
|------|--------|-------|-------|------|-----------|-------------|
| Test 1 | 50 | 2 | 7 | Find limit between 36-50 | 1h | 100k |
| Test 2 | 100 | 2 | 7 | Find limit between 50-100 | 2h | 200k |
| Test 3 | 5+ | 5 | 7 | Test deep nesting | 1h | 80k |
| Test 4 | 10 | 2 | 10 | All agent types | 1h | 60k |
| Test 5 | 20+ | 2 | 1 | Same-type concurrency | 1h | 80k |
| Test 6 | 36 | 2-4 | 7 | Wide vs Deep | 2h | 120k |
| Test 7 | 2500+ | 2 | 7 | Stress test | 4h | 300k |
| **Total** | | | | | **12h** | **940k** |

---

## Test 1: 50 Concurrent Agents (Week 1, Day 1)

**Goal:** Find limit between proven 36 and untested 50

**Setup:**
```bash
# Create test task
cat > /tmp/test-50-agents.txt << 'EOF'
Create 50 parallel agents for analysis:
  - 20 engineers
  - 15 lead-engineers
  - 10 senior-engineers
  - 3 quality-engineers
  - 1 security-engineer
  - 1 orchestrator

Each agent should:
  1. Analyze a different microservice (simulated)
  2. Report findings in 500 words
  3. Estimate 20k tokens per agent

Monitor with:
  opencode-tokens --session <id>
  watch -n 5 'opencode-tokens --session <id>'
EOF

# Run test
opencode run "$(cat /tmp/test-50-agents.txt)"
```

**Success Criteria:**
- ✅ All 50 agents spawn successfully
- ✅ No errors in logs
- ✅ All agents complete within 2 hours
- ✅ Total tokens ≤ 100k
- ✅ Peak concurrent agents = 50

**Failure Modes:**
- ❌ Spawn fails at N agents (record N)
- ❌ Agents timeout (>2 hours)
- ❌ Token budget exceeded
- ❌ Orchestrator crashes

**Expected Outcome:**
- If success: Proceed to Test 2 (100 agents)
- If failure at N: Adjust Test 2 to N-5 agents

---

## Test 2: 100 Concurrent Agents (Week 1, Day 2-3)

**Goal:** Find limit between 50 and 100

**Setup:**
```bash
cat > /tmp/test-100-agents.txt << 'EOF'
Create 100 parallel agents for analysis:
  - 40 engineers
  - 30 lead-engineers
  - 20 senior-engineers
  - 7 quality-engineers
  - 2 security-engineers
  - 1 orchestrator

Each agent should:
  1. Analyze a different microservice (simulated)
  2. Report findings in 500 words
  3. Estimate 20k tokens per agent

Monitor with:
  opencode-tokens --session <id>
  watch -n 5 'opencode-tokens --session <id>'
EOF

opencode run "$(cat /tmp/test-100-agents.txt)"
```

**Success Criteria:**
- ✅ All 100 agents spawn successfully
- ✅ No errors in logs
- ✅ All agents complete within 3 hours
- ✅ Total tokens ≤ 200k
- ✅ Peak concurrent agents = 100

**Failure Modes:**
- ❌ Spawn fails at N agents (record N)
- ❌ Agents timeout (>3 hours)
- ❌ Token budget exceeded
- ❌ Orchestrator crashes

**Expected Outcome:**
- If success: Proceed to Test 7 (stress test 2500+)
- If failure at N: Adjust Test 7 to N-10 agents

---

## Test 3: 5+ Tiers Deep (Week 1, Day 4)

**Goal:** Test deep nesting (currently proven to 4 tiers)

**Setup:**
```bash
cat > /tmp/test-deep-nesting.txt << 'EOF'
Create nested agent hierarchy:

Tier 1 (Orchestrator):
  └─ Tier 2 (Senior Engineer):
      ├─ Tier 3 (Lead Engineer):
      │   ├─ Tier 4 (Quality Engineer):
      │   │   ├─ Tier 5 (Engineer):
      │   │   │   └─ Tier 6 (Explore):
      │   │   │       └─ Tier 7 (General):
      │   │   │           └─ Tier 8 (Build):
      │   │   │               └─ Tier 9 (Principal Engineer):
      │   │   │                   └─ Tier 10 (Security Engineer):

Each tier should:
  1. Create child task
  2. Wait for child to complete
  3. Report findings

Monitor with:
  opencode-subagents --session <id>
  sqlite3 ~/.local/share/opencode/opencode.db "
    WITH RECURSIVE depth_calc AS (
      SELECT id, parent_id, 1 as depth FROM session WHERE parent_id IS NULL
      UNION ALL
      SELECT s.id, s.parent_id, d.depth + 1 FROM session s
      INNER JOIN depth_calc d ON s.parent_id = d.id
    )
    SELECT MAX(depth) as max_depth FROM depth_calc;
  "
EOF

opencode run "$(cat /tmp/test-deep-nesting.txt)"
```

**Success Criteria:**
- ✅ Nesting reaches at least 5 tiers
- ✅ No depth limit errors
- ✅ All tiers complete successfully
- ✅ Total tokens ≤ 80k
- ✅ Max depth = 5+ (record actual)

**Failure Modes:**
- ❌ Depth limit hit at tier N (record N)
- ❌ Timeout waiting for child
- ❌ Token budget exceeded

**Expected Outcome:**
- If success: Depth limit is ≥5 (likely higher)
- If failure at tier N: Depth limit is N-1

---

## Test 4: All 10 Agent Types (Week 2, Day 1)

**Goal:** Verify all agent types work in parallel

**Setup:**
```bash
cat > /tmp/test-all-types.txt << 'EOF'
Create 10 parallel agents (one of each type):
  1. orchestrator
  2. engineer
  3. lead-engineer
  4. senior-engineer
  5. principal-engineer
  6. quality-engineer
  7. security-engineer
  8. explore
  9. build
  10. general

Each agent should:
  1. Perform type-specific task
  2. Report completion
  3. Estimate 6k tokens per agent

Monitor with:
  opencode-subagents --session <id>
  sqlite3 ~/.local/share/opencode/opencode.db "
    SELECT agent, COUNT(*) 
    FROM session 
    WHERE parent_id = '<parent-id>' 
    GROUP BY agent;
  "
EOF

opencode run "$(cat /tmp/test-all-types.txt)"
```

**Success Criteria:**
- ✅ All 10 types spawn successfully
- ✅ No type conflicts or errors
- ✅ All agents complete within 1 hour
- ✅ Total tokens ≤ 60k
- ✅ All 10 types present in output

**Failure Modes:**
- ❌ Type X fails to spawn
- ❌ Type X conflicts with type Y
- ❌ Type X timeout

**Expected Outcome:**
- If success: All types work in parallel (proven)
- If failure: Document which types don't work together

---

## Test 5: 20+ Same Agent Type (Week 2, Day 2)

**Goal:** Test same-type concurrency (currently proven to 17 engineers)

**Setup:**
```bash
cat > /tmp/test-same-type.txt << 'EOF'
Create 20 parallel engineers:
  - 20 engineers (same type)
  - Each analyzes different code file
  - Each reports findings in 500 words
  - Estimate 20k tokens per agent

Monitor with:
  opencode-subagents --session <id>
  sqlite3 ~/.local/share/opencode/opencode.db "
    SELECT agent, COUNT(*) 
    FROM session 
    WHERE parent_id = '<parent-id>' 
    GROUP BY agent;
  "
EOF

opencode run "$(cat /tmp/test-same-type.txt)"
```

**Success Criteria:**
- ✅ All 20 engineers spawn successfully
- ✅ No same-type conflicts
- ✅ All agents complete within 1 hour
- ✅ Total tokens ≤ 80k
- ✅ All 20 engineers present in output

**Failure Modes:**
- ❌ Spawn fails at N engineers
- ❌ Same-type conflict detected
- ❌ Timeout

**Expected Outcome:**
- If success: Same-type limit is ≥20 (likely higher)
- If failure at N: Same-type limit is N-1

---

## Test 6: Wide vs Deep Comparison (Week 2, Day 3-4)

**Goal:** Compare performance of wide (many children) vs deep (many tiers) strategies

**Setup A: Wide (36 children, 2 tiers)**
```bash
cat > /tmp/test-wide.txt << 'EOF'
Create wide hierarchy:
  Tier 1: Orchestrator
    └─ Tier 2: 36 parallel agents (mixed types)

Monitor:
  - Peak concurrent agents
  - Total tokens
  - Wall-clock time
  - Quality score
EOF

opencode run "$(cat /tmp/test-wide.txt)"
```

**Setup B: Deep (6 tiers, 2 children each)**
```bash
cat > /tmp/test-deep.txt << 'EOF'
Create deep hierarchy:
  Tier 1: Orchestrator
    └─ Tier 2: Senior Engineer
        └─ Tier 3: Lead Engineer
            └─ Tier 4: Quality Engineer
                └─ Tier 5: Engineer
                    └─ Tier 6: Explore

Monitor:
  - Peak concurrent agents
  - Total tokens
  - Wall-clock time
  - Quality score
EOF

opencode run "$(cat /tmp/test-deep.txt)"
```

**Success Criteria:**
- ✅ Both wide and deep complete successfully
- ✅ Compare metrics side-by-side
- ✅ Document tradeoffs

**Metrics to Compare:**
| Metric | Wide | Deep | Winner |
|--------|------|------|--------|
| Peak concurrent | 36 | 2 | Wide (faster) |
| Total tokens | 720k | 60k | Deep (cheaper) |
| Wall-clock time | 1h | 2h | Wide (faster) |
| Quality score | 85 | 92 | Deep (better) |

**Expected Outcome:**
- Wide: Faster, higher token cost, lower quality
- Deep: Slower, lower token cost, higher quality

---

## Test 7: Stress Test (2500+ Agents) (Week 2-3, Day 5+)

**Goal:** Find absolute limit of concurrent agents

**Setup:**
```bash
cat > /tmp/test-stress.txt << 'EOF'
Create massive parallel task:
  - 2500 agents (or as many as system allows)
  - Mixed types (proportional distribution)
  - Each agent: minimal task (1k tokens)
  - Total: 2500k tokens

Monitor:
  - Peak concurrent agents
  - When spawn fails (if it does)
  - System resource usage
  - Orchestrator stability

Commands:
  opencode-tokens --session <id>
  opencode-subagents --session <id>
  sqlite3 ~/.local/share/opencode/opencode.db "
    SELECT parent_id, COUNT(*) as children 
    FROM session 
    WHERE parent_id IS NOT NULL 
    GROUP BY parent_id 
    ORDER BY children DESC;
  "
EOF

opencode run "$(cat /tmp/test-stress.txt)"
```

**Success Criteria:**
- ✅ Spawn as many agents as possible
- ✅ Record actual limit (if hit)
- ✅ Document system behavior at limit
- ✅ No crashes or data loss

**Failure Modes:**
- ❌ Spawn fails at N agents (record N)
- ❌ Orchestrator crashes
- ❌ Database corruption
- ❌ Token budget exceeded

**Expected Outcome:**
- Find actual limit (likely 100+, possibly 1000+)
- Document system behavior at limit
- Recommend safe operating range

---

## Execution Plan

### Week 1 (Tests 1-3)
- **Day 1:** Test 1 (50 agents)
- **Day 2-3:** Test 2 (100 agents)
- **Day 4:** Test 3 (5+ tiers)

### Week 2 (Tests 4-6)
- **Day 1:** Test 4 (all 10 types)
- **Day 2:** Test 5 (20+ same type)
- **Day 3-4:** Test 6 (wide vs deep)

### Week 2-3 (Test 7)
- **Day 5+:** Test 7 (stress test 2500+)

### Analysis & Documentation
- **Week 3:** Analyze all results
- **Week 3:** Update CONCURRENT-SUBAGENT-CAPACITY.md
- **Week 3:** Create testing report

---

## Monitoring During Tests

### Real-Time Monitoring
```bash
# Terminal 1: Run test
opencode run "..."

# Terminal 2: Monitor tokens
SESSION_ID=$(sqlite3 ~/.local/share/opencode/opencode.db \
  "SELECT id FROM session ORDER BY time_created DESC LIMIT 1;")
watch -n 5 "opencode-tokens --session $SESSION_ID"

# Terminal 3: Monitor subagents
watch -n 5 "opencode-subagents --session $SESSION_ID"

# Terminal 4: Monitor database
watch -n 10 "sqlite3 ~/.local/share/opencode/opencode.db \
  'SELECT parent_id, COUNT(*) as children FROM session 
   WHERE parent_id IS NOT NULL GROUP BY parent_id ORDER BY children DESC;'"
```

### Data Collection
```bash
# After each test, export metrics
SESSION_ID=<test-session-id>
opencode-tokens --session $SESSION_ID --format json > test-N-metrics.json
opencode-subagents --session $SESSION_ID --format json > test-N-subagents.json

# Archive results
mkdir -p testing-results/test-N
cp test-N-metrics.json testing-results/test-N/
cp test-N-subagents.json testing-results/test-N/
```

---

## Success Criteria (Overall)

✅ **Test 1 Success:** 50 agents spawn and complete
✅ **Test 2 Success:** 100 agents spawn and complete
✅ **Test 3 Success:** 5+ tiers deep nesting works
✅ **Test 4 Success:** All 10 agent types work in parallel
✅ **Test 5 Success:** 20+ same-type agents work
✅ **Test 6 Success:** Wide vs deep comparison complete
✅ **Test 7 Success:** Find actual limit (or reach 2500+)

**Overall Goal:** Determine actual concurrent subagent limit and document safe operating range.

---

## Expected Findings

Based on proven 36 agents and no observed limits:

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| Limit ≥ 50 | High | 36 proven, no errors |
| Limit ≥ 100 | Medium | Likely, but untested |
| Limit ≥ 500 | Low | Possible, but untested |
| Limit ≥ 1000 | Very Low | Possible, but untested |
| Limit = ∞ | Very Low | Unlikely, but possible |

**Most Likely Outcome:** Limit is 100-500 agents (based on typical system constraints).

---

## Documentation Updates

After all tests complete:

1. **Update CONCURRENT-SUBAGENT-CAPACITY.md**
   - Add actual findings
   - Update proven limits table
   - Add test results

2. **Create TESTING-RESULTS.md**
   - Test 1-7 results
   - Metrics comparison
   - Recommendations

3. **Update MAX-CONCURRENT-SUBAGENTS.md**
   - New safe operating range
   - Recommendations for different scenarios

4. **Create CAPACITY-PLANNING-GUIDE.md**
   - How to estimate agents needed
   - How to monitor during execution
   - How to handle limit reached

---

## Budget

| Test | Tokens | Cost |
|------|--------|------|
| Test 1 (50 agents) | 100k | $3.00 |
| Test 2 (100 agents) | 200k | $6.00 |
| Test 3 (5+ tiers) | 80k | $2.40 |
| Test 4 (all types) | 60k | $1.80 |
| Test 5 (20+ same) | 80k | $2.40 |
| Test 6 (wide vs deep) | 120k | $3.60 |
| Test 7 (stress) | 300k | $9.00 |
| **Total** | **940k** | **$28.20** |

**Note:** Costs are estimates based on Haiku pricing ($0.00003/token). Actual costs may vary based on model mix.

---

**Status:** Ready to execute
**Start Date:** Week 1, Day 1 (2026-05-20)
**Expected Completion:** Week 3 (2026-06-02)
**Owner:** Orchestrator (with Quality Engineer oversight)
