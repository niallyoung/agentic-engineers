# agentic-engineers Skills Registry

Reusable workflows and automated skills triggered by events in the system.

---

## Skills Overview

A **Skill** is a reusable, event-triggered workflow that coordinates multiple agents to accomplish a specific goal. Skills are invoked automatically (via git hooks, file watchers, scheduled jobs) or manually via CLI.

---

## 1. SPEC REVIEW SKILL ⭐ (CRITICAL)

**Purpose:** Automatically review SPEC.md when it changes, ensure consistency/completeness/architectural soundness.

**Trigger:** SPEC.md file modified (detected in pre-push or post-commit hook)

**Workflow:**

```
SPEC.md modified
  ↓
Detect change (git diff)
  ↓
SpecEngineerOrchestrator receives DELEGATE:
  ├─ task_id: 2026-04-29-spec-review-<hash>
  ├─ scope: "Review updated SPEC.md"
  ├─ spec_content: <full SPEC.md>
  ├─ previous_spec: <HEAD~1 version>
  └─ diff: <git diff SPEC.md>
  ↓
Orchestrator delegates in PARALLEL to 4 agents:
  ├─ ConsistencyReviewer (contradictions, broken refs)
  ├─ ArchitectureReviewer (self-contained constraint, delegations)
  ├─ CompletenessReviewer (agents, protocols, examples documented)
  └─ SecurityReviewer (security implications, constraints)
  ↓
Orchestrator aggregates 4 HANDBACK blocks
  ↓
Decision:
  ├─ If TYPE_A or TYPE_D found → NEEDS_REVISION (block commit)
  ├─ If TYPE_B or TYPE_C found → NEEDS_REVIEW (flag for human)
  └─ If no issues → APPROVED (allow commit)
  ↓
Output: HANDBACK block with findings
  ├─ status: APPROVED | NEEDS_REVISION | NEEDS_REVIEW
  ├─ issues_found: {...}
  ├─ recommendations: [...]
  └─ confidence: 0.0-1.0
```

**Implementation Status:** ⚠️ **Needs to be built** (Spec Engineer agents are currently stubs)

**Critical Steps:**
1. Flesh out SpecEngineerOrchestrator logic
2. Implement ConsistencyReviewer agent
3. Implement ArchitectureReviewer agent
4. Implement CompletenessReviewer agent
5. Implement SecurityReviewer agent
6. Wire into git pre-push hook

**Success Criteria:**
- ✅ All review agents run in parallel
- ✅ <30s total latency
- ✅ Zero TYPE_A/D issues leak through
- ✅ <2% false positives on TYPE_B/C
- ✅ Clear recommendations for fixes

**Example Triggers:**

```bash
# Trigger 1: Developer modifies SPEC.md and pushes
git add docs/SPEC.md
git commit -m "feat: update routing tree"
git push
  → Pre-push hook detects SPEC.md change
  → Invokes SPEC REVIEW SKILL
  → Returns APPROVED/NEEDS_REVISION

# Trigger 2: Manual review request
agentic-engineers review-spec --file docs/SPEC.md
  → Invokes SPEC REVIEW SKILL immediately

# Trigger 3: Scheduled weekly review
(Every Monday 9am via cron)
  → Invokes SPEC REVIEW SKILL on current main branch
  → Reports findings
```

---

## 2. QUALITY GATE SKILL

**Purpose:** Synchronously validate every commit against security/testing/metrics/health/spec criteria.

**Trigger:** 
- Commit created (pre-commit hook)
- Code merged to main (post-merge hook)
- Manual: `agentic-engineers quality-gate`

**Workflow:**

```
Code committed/merged
  ↓
QualityGateOrchestrator receives DELEGATE:
  ├─ task_id: <git_sha>
  ├─ scope: "Quality gate validation"
  ├─ code_diff: <git diff>
  ├─ test_output: <make test output>
  ├─ metrics: <system health snapshot>
  └─ config_changes: <config diff if any>
  ↓
Orchestrator delegates in PARALLEL (5 agents, ~20-30ms each):
  ├─ SecurityAgentQG (scan credentials, vulns)
  ├─ TestingAgent (validate tests, coverage)
  ├─ MetricsAgent (check system health)
  ├─ HealingAgent (verify configs)
  └─ SpecEngineerAgent (detect spec drift)
  ↓
Orchestrator aggregates 5 HANDBACK blocks
  ↓
Decision:
  ├─ All 5 PASS → PROCEED (allow merge)
  └─ Any ESCALATE → ESCALATE (block, require fix)
  ↓
Output: HANDBACK block
  ├─ decision: PROCEED | ESCALATE
  ├─ agents_passed: N
  ├─ agents_escalated: N
  ├─ audit_trail: [{agent, status}, ...]
  └─ confidence: 0.0-1.0
```

**Implementation Status:** ✅ **Stub complete, ready for agent implementation**

**Success Criteria:**
- ✅ <30s total latency (5 agents in parallel)
- ✅ 0% false positives on clean commits
- ✅ <2% false negatives on escalable issues
- ✅ ~$0.31 cost per commit

**Example Triggers:**

```bash
# Trigger 1: Local pre-commit
git commit -m "feat: new feature"
  → Pre-commit hook invokes QUALITY GATE
  → Returns PROCEED/ESCALATE
  → Blocks if ESCALATE

# Trigger 2: Pre-push validation
git push
  → Pre-push hook runs E2E tests
  → Waits for QG result
  → Confirms with user before push

# Trigger 3: Post-merge on main
(After PR merge)
  → Post-merge hook invokes QUALITY GATE
  → Records decision in artifacts/
  → Notifies if ESCALATE
```

---

## 3. SDLC ORCHESTRATION SKILL

**Purpose:** Route incoming engineering tasks to appropriate specialist agent, coordinate execution, collect feedback.

**Trigger:**
- New task request (CLI, API, issue)
- Manual: `agentic-engineers execute-task --scope "..."`

**Workflow:**

```
Task received
  ↓
GeneralOrchestrator routes via 6-point tree:
  ├─ is_security? → SecurityEngineer
  ├─ high complexity, no plan? → SeniorEngineer
  ├─ has plan? → Engineer
  └─ else → LeadEngineer
  ↓
Selected agent executes work
  (may delegate to sub-agents)
  ↓
QualityEngineer reviews execution
  ↓
ModelEngineer calculates confidence
  ↓
Output: HANDBACK block
  ├─ deliverables: [...]
  ├─ quality_score: 0-100
  ├─ confidence: 0.0-1.0
  └─ token_metrics: {...}
  ↓
Feedback loops (async):
  ├─ QG Feedback: analyze patterns
  ├─ Model Engineer: recommend models
  └─ Config Enforcement: apply fixes
```

**Implementation Status:** ✅ **Stub complete, ready for agent implementation**

**Success Criteria:**
- ✅ Correct routing 100% per 6-point tree
- ✅ 80-95% quality score on execution
- ✅ Confidence algorithm correctly applied
- ✅ All deliverables documented

---

## 4. SPEC DRIFT DETECTION (Integrated into QG)

**Purpose:** As part of Quality Gate, detect spec/code divergence (TYPE_A/B/C/D).

**Trigger:** Quality Gate executes (every commit)

**Within SpecEngineerAgent (QG sub-agent):**

```
Code commit diff received
  ↓
SpecEngineerAgent delegates to 4 sub-agents:
  ├─ Check TYPE_A: features documented but missing in code
  ├─ Check TYPE_B: features in code but undocumented
  ├─ Check TYPE_C: spec and code describe same feature differently
  └─ Check TYPE_D: breaking changes without deprecation path
  ↓
Aggregates findings
  ↓
Output:
  ├─ drift_types: [TYPE_A, TYPE_B, TYPE_C, TYPE_D]
  ├─ severity: PASS | LOW | MEDIUM | HIGH
  └─ confidence: 0.0-1.0
```

**Integration:** Runs as part of QG, decision:
- TYPE_A or TYPE_D found → ESCALATE (mandatory fix)
- TYPE_B or TYPE_C found → Flag for review
- No issues → PASS

---

## 5. FEEDBACK AGGREGATION SKILL

**Purpose:** Collect, analyze, and act on feedback from agents to continuously optimize system.

**Trigger:** After SDLC agent completes execution (async)

**Workflow:**

```
HANDBACK blocks collected
  ↓
3 Feedback Loops run in parallel:

1. QG Feedback Handler:
   ├─ Aggregate HANDBACK from agents
   ├─ Identify patterns/issues
   └─ Generate FEEDBACK block

2. Model Engineer Feedback:
   ├─ Analyze token usage trends
   ├─ Compare quality vs cost
   └─ Recommend model downgrades/upgrades

3. Config Enforcement:
   ├─ Identify config issues
   ├─ Auto-apply fixes (confidence >0.95)
   ├─ Escalate for review (0.80-0.95)
   └─ Request human intervention (<0.80)
  ↓
All FEEDBACK blocks → artifacts/feedback/patterns/
  ↓
Patterns database updated for next similar tasks
```

**Implementation Status:** ⚠️ **Stub agents exist, full integration needed**

---

## 6. MODEL SELECTION SKILL

**Purpose:** Recommend optimal model for future similar tasks based on quality/cost analysis.

**Trigger:** After ModelEngineer generates recommendations (async)

**Logic:**

```
Task completed
  ↓
ModelEngineer analyzes:
  ├─ Quality score achieved
  ├─ Token usage (input + output)
  ├─ Confidence in result
  ├─ Model used
  └─ Task type/complexity
  ↓
Generates recommendation:
  ├─ rank_1_model: recommended (best quality)
  ├─ rank_2_model: alternate (cost-effective)
  ├─ confidence: 0.0-1.0
  └─ reasoning: why
  ↓
Stored in artifacts/patterns/ for:
  - Future similar tasks
  - Cost optimization analysis
  - Model distribution trends
```

**Example:**

```
Task: "Add timeout grace period"
Quality achieved: 95%
Token usage: 2,450 (input) + 840 (output)
Model used: Haiku 4.5

Recommendation:
  - Rank 1: Haiku 4.5 (achieved excellent quality)
  - Reason: This task type well-suited to Haiku's capabilities
  - Cost: $0.009 (very cheap)
  - Confidence: 0.95

For next similar task:
  → Use Haiku 4.5 (unless complexity increases)
```

---

## Git Hook Integration

### Pre-Commit Hook

```bash
#!/bin/bash
# Runs: make lint, make test, spec validation (if SPEC.md changed)

make lint       # Linter
make test       # Unit tests

if git diff --cached --name-only | grep -q "docs/SPEC.md"; then
    agentic-engineers review-spec --exit-on-revision
    # Exits with error if NEEDS_REVISION
    # Allows if APPROVED
fi
```

### Pre-Push Hook

```bash
#!/bin/bash
# Runs: E2E tests, color diff review, quality gate validation

make e2e        # E2E tests
make diff       # Color diff review with user prompt

# Trigger Quality Gate if this affects main
agentic-engineers quality-gate --commit-sha $COMMIT_SHA
# Blocks push if ESCALATE
```

---

## Manual Skill Invocation

```bash
# Review SPEC.md
agentic-engineers review-spec --file docs/SPEC.md

# Run Quality Gate on current commit
agentic-engineers quality-gate

# Execute a task
agentic-engineers execute-task --scope "Add feature X" --complexity high

# Analyze token usage trends
agentic-engineers analyze-tokens --period week

# Get model recommendations for next task
agentic-engineers recommend-models --task-type "timeout-fix"
```

---

## Skill Status Summary

| Skill | Purpose | Status | Trigger | Latency |
|-------|---------|--------|---------|---------|
| SPEC REVIEW | Validate SPEC.md changes | ⚠️ Needs impl | SPEC.md modified | <30s |
| QUALITY GATE | Validate every commit | ✅ Stub ready | Pre-push/merge | <30s |
| SDLC ORCH | Route & execute tasks | ✅ Stub ready | Task request | Variable |
| SPEC DRIFT | Detect TYPE_A/B/C/D | ⚠️ Sub-agents need impl | Every commit | <5s (in QG) |
| FEEDBACK | Analyze patterns | ⚠️ Handlers need impl | After execution | Async |
| MODEL SEL | Recommend models | ⚠️ Needs impl | After execution | Async |

---

## Critical Implementation Path

**Phase 1 (Week 1-2):** Core SDLC + QG agents
- Implement 14 agents (stubs → real implementations)
- Wire Quality Gate hook

**Phase 2 (Week 2-3):** Spec Review System
1. Implement SpecEngineerOrchestrator
2. Implement ConsistencyReviewer agent
3. Implement ArchitectureReviewer agent
4. Implement CompletenessReviewer agent
5. Implement SecurityReviewer agent
6. Wire SPEC REVIEW SKILL into pre-push hook

**Phase 3 (Week 3-4):** Feedback Loops
- Implement feedback handlers
- Wire Model Selection logic
- Complete full system integration

---

**Total Skills:** 6 core + 2 integrations  
**Critical for ship:** SPEC REVIEW SKILL (automated spec validation)  
**Enables:** Self-maintaining system where spec and code stay in sync
