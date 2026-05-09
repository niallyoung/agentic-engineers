---
name: Quality Gate Testing Framework
description: Comprehensive testing infrastructure for Quality Gate validation (10+ test commits, baseline accuracy)
phase: 6
status: IMPLEMENTATION_READY
---

# Quality Gate Testing Framework

**Objective**: Validate Quality Gate makes correct PROCEED/ESCALATE decisions on 10+ test commits with 0% false positive rate.

**Success Criteria**:
- ✅ 10/10 correct decisions (PROCEED vs. ESCALATE as expected)
- ✅ Spec Engineer detects all 4 drift types (TYPE_A/B/C/D)
- ✅ 0% false positives on clean commits
- ✅ <2% false negatives (miss escalable issues)
- ✅ Cost baseline verified ($0.31/commit)
- ✅ Latency < 30 sec (all 5 sub-agents parallel)

---

## Test Scenario Design

### 10 Test Commits

| # | Name | Expected | Triggers | Description |
|---|------|----------|----------|-------------|
| 1 | **Clean** | PROCEED | None | Good code, tests pass, no issues, spec-aligned |
| 2 | **Security** | ESCALATE | Security | Hardcoded credentials detected |
| 3 | **Test Failure** | ESCALATE | Testing | 1+ test fails, coverage < 80% |
| 4 | **Metrics** | ESCALATE | Metrics | Health score < 70 (latency/errors/capacity) |
| 5 | **Config Drift** | ESCALATE | Healing | Environment variable mismatch or CDK param wrong |
| 6 | **Regression** | ESCALATE | Spec Engineer (TYPE_A) | Documented feature missing from code |
| 7 | **Undocumented** | ESCALATE | Spec Engineer (TYPE_B) | Code feature not in SPEC.md |
| 8 | **Mismatch** | ESCALATE | Spec Engineer (TYPE_C) | Agent model doesn't match spec |
| 9 | **Breaking Change** | ESCALATE | Spec Engineer (TYPE_D) | Documented feature deleted without deprecation |
| 10 | **Mixed Issues** | ESCALATE | Multiple | Security + test failure + config drift |

---

## Test Scenarios (Detailed)

### Scenario 1: Clean Commit (Expected: PROCEED)

**Setup**:
- Create feature branch: `git checkout -b test-clean-commit`
- Add valid code (no issues)
- All tests pass
- No config drift
- Spec-aligned (no undocumented changes)

**Code**:
```python
# New file: lib/utils.py
def calculate_hash(data: str) -> str:
    """Calculate SHA-256 hash of input data."""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()

# Test: test/test_utils.py
def test_calculate_hash():
    assert calculate_hash("hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
```

**Expected Handbacks**:
- Security Agent: PASS (no credentials)
- Testing Agent: PASS (tests pass, coverage ≥80%)
- Metrics Agent: PASS (health_score ≥70)
- Healing Agent: PASS (no config issues)
- Spec Engineer: PASS (no drift, 100% compliance)

**QG Decision**: **PROCEED** ✓

---

### Scenario 2: Security Issue (Expected: ESCALATE)

**Setup**:
- Add hardcoded API key to code

**Code**:
```python
# Bad code with hardcoded credential
API_KEY = "sk-1234567890abcdefghijklmnopqrstuv"  # ← SECURITY ISSUE

def authenticate():
    return {"Authorization": f"Bearer {API_KEY}"}
```

**Expected Handbacks**:
- Security Agent: **ESCALATE** HIGH (hardcoded credential detected)
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: PASS

**QG Decision**: **ESCALATE** ✓ (Security HIGH → immediate escalation)

---

### Scenario 3: Test Failure (Expected: ESCALATE)

**Setup**:
- Add code that breaks existing tests
- Coverage drops below 80%

**Code**:
```python
# Code change that breaks tests
def calculate_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()  # REMOVED ERROR HANDLING

# Test fails:
def test_calculate_hash_empty():
    assert calculate_hash("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    # ^ FAILS because we removed validation
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: **ESCALATE** (1 test failed, coverage < 80%)
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: PASS

**QG Decision**: **ESCALATE** ✓ (Testing failure → escalation)

---

### Scenario 4: Metrics Degradation (Expected: ESCALATE)

**Setup**:
- Simulate high latency or error rate in metrics

**Metrics Simulation**:
```yaml
latency_p99: 5000ms  # Target: <500ms → DEGRADED
error_rate: 15%      # Target: <5% → DEGRADED
health_score: 45     # FAIL (< 70)
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: **ESCALATE** (health_score < 70)
- Healing Agent: PASS
- Spec Engineer: PASS

**QG Decision**: **ESCALATE** ✓ (Metrics < threshold → escalation)

---

### Scenario 5: Configuration Drift (Expected: ESCALATE)

**Setup**:
- Environment variable mismatch (e.g., `LOG_LEVEL` changed without approval)

**Config Issue**:
```yaml
Current State:
  LOG_LEVEL: "debug"
Expected State (from spec):
  LOG_LEVEL: "info"
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: **ESCALATE** (config mismatch detected)
- Spec Engineer: PASS

**QG Decision**: **ESCALATE** ✓ (Healing escalation → escalation)

---

### Scenario 6: Regression (TYPE_A, Expected: ESCALATE)

**Setup**:
- Delete a documented agent from code
- SPEC.md documents it; code doesn't have it

**Code Change**:
```
❌ DELETE: orchestration/agents/engineer-agent.md
   (Documented in SPEC.md but removed from code)
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: **ESCALATE** (TYPE_A: documented feature missing)

**QG Decision**: **ESCALATE** ✓ (Spec drift TYPE_A → escalation)

---

### Scenario 7: Undocumented Change (TYPE_B, Expected: ESCALATE)

**Setup**:
- Add new agent not documented in SPEC.md

**Code Change**:
```
✅ ADD: orchestration/agents/logging-agent.md
   (Code added but SPEC.md doesn't mention it)
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: **ESCALATE** (TYPE_B: undocumented feature)

**QG Decision**: **ESCALATE** ✓ (Spec drift TYPE_B → escalation)

---

### Scenario 8: Spec/Code Mismatch (TYPE_C, Expected: ESCALATE)

**Setup**:
- Change agent model but don't update SPEC.md

**Code Change**:
```yaml
# orchestration/agents/senior-engineer-agent.md
OLD: Model: claude-sonnet-4-5
NEW: Model: claude-sonnet-4-7  # ← Changed, SPEC.md still says 4-5
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: **ESCALATE** (TYPE_C: spec/code mismatch)

**QG Decision**: **ESCALATE** ✓ (Spec drift TYPE_C → escalation)

---

### Scenario 9: Breaking Change (TYPE_D, Expected: ESCALATE)

**Setup**:
- Delete a critical documented feature without deprecation

**Code Change**:
```
❌ DELETE: orchestration/agents/quality-gate-orchestrator-agent.md
   (SPEC.md documents this as core; deleted without deprecation)
   NO deprecation notice in SPEC.md
```

**Expected Handbacks**:
- Security Agent: PASS
- Testing Agent: PASS
- Metrics Agent: PASS
- Healing Agent: PASS
- Spec Engineer: **ESCALATE** (TYPE_D: breaking change without deprecation)

**QG Decision**: **ESCALATE** ✓ (Spec drift TYPE_D → escalation)

---

### Scenario 10: Mixed Issues (Expected: ESCALATE)

**Setup**:
- Combine: security issue + test failure + config drift

**Issues**:
1. Hardcoded API key (Security issue)
2. Tests fail (coverage < 80%)
3. Environment variable mismatch

**Expected Handbacks**:
- Security Agent: **ESCALATE** (hardcoded credential)
- Testing Agent: **ESCALATE** (tests fail)
- Metrics Agent: PASS
- Healing Agent: **ESCALATE** (config drift)
- Spec Engineer: PASS

**QG Decision**: **ESCALATE** ✓ (Multiple escalations → ESCALATE)

---

## Test Execution Protocol

### Phase 1: Preparation

```bash
# 1. Create test branch
git checkout -b phase-6-qg-testing

# 2. Set up test artifacts directory
mkdir -p artifacts/qg-testing
mkdir -p artifacts/qg-testing/scenarios

# 3. Initialize test framework
cd orchestration
python QUALITY-GATE-TEST-FRAMEWORK.py --init
```

### Phase 2: Run Each Scenario

```bash
# For each scenario (1-10):
python QUALITY-GATE-TEST-FRAMEWORK.py \
  --scenario 1 \
  --expected-decision PROCEED \
  --name "clean-commit"

# Expected output:
# ✓ Running scenario 1: clean-commit
# ✓ Expected decision: PROCEED
# ✓ Generated test commit
# ✓ Running Quality Gate...
# ✓ Security Agent: PASS
# ✓ Testing Agent: PASS
# ✓ Metrics Agent: PASS
# ✓ Healing Agent: PASS
# ✓ Spec Engineer: PASS
# ✓ Quality Gate Decision: PROCEED
# ✓ Result: PASS ✅
```

### Phase 3: Verify Results

```bash
# Check test artifacts
ls -la artifacts/qg-testing/scenarios/

# Should see:
# DELEGATE-scenario-1-clean-commit.yaml
# HANDBACK-scenario-1-security-agent.yaml
# HANDBACK-scenario-1-testing-agent.yaml
# HANDBACK-scenario-1-metrics-agent.yaml
# HANDBACK-scenario-1-healing-agent.yaml
# HANDBACK-scenario-1-spec-engineer.yaml
# HANDBACK-scenario-1-qg-orchestrator.yaml

# Generate summary report
python QUALITY-GATE-TEST-FRAMEWORK.py --generate-report
```

### Phase 4: Measure Metrics

```bash
# Calculate accuracy
#   Correct decisions: 10/10
#   Accuracy: 100%

# Calculate cost
#   Total cost: $0.31 × 10 = $3.10
#   Average cost per commit: $0.31 ✓

# Calculate latency
#   Average QG execution time: 25 sec
#   Target: < 30 sec ✓
```

---

## Acceptance Criteria

### Functional

- [ ] Scenario 1 (Clean): PASS → PROCEED ✓
- [ ] Scenario 2 (Security): ESCALATE → ESCALATE ✓
- [ ] Scenario 3 (Test Failure): ESCALATE → ESCALATE ✓
- [ ] Scenario 4 (Metrics): ESCALATE → ESCALATE ✓
- [ ] Scenario 5 (Config Drift): ESCALATE → ESCALATE ✓
- [ ] Scenario 6 (TYPE_A): ESCALATE → ESCALATE ✓
- [ ] Scenario 7 (TYPE_B): ESCALATE → ESCALATE ✓
- [ ] Scenario 8 (TYPE_C): ESCALATE → ESCALATE ✓
- [ ] Scenario 9 (TYPE_D): ESCALATE → ESCALATE ✓
- [ ] Scenario 10 (Mixed): ESCALATE → ESCALATE ✓

### Quality Metrics

- [ ] **Accuracy**: 10/10 correct decisions (100%)
- [ ] **False Positives**: 0 (no false escalations on clean commits)
- [ ] **False Negatives**: 0 (catch all issues)
- [ ] **Cost**: $0.31/commit (matches projection)
- [ ] **Latency**: < 30 sec for all 5 agents parallel

### Documentation

- [ ] Test results documented in artifacts/
- [ ] Summary report generated
- [ ] All DELEGATE/HANDBACK blocks saved
- [ ] Confidence scores recorded

---

## Phase 6 Timeline

| Week | Task | Owner |
|------|------|-------|
| Week 1 | Implement SDLC agents | Senior Engineer + Lead Engineer |
| Week 2 | Implement QG sub-agents | Lead Engineer + Quality Engineer |
| Week 3 | Run 10 test commits through QG | All agents |
| Week 4 | Analyze results, tune, document | Lead Engineer |

---

## Success Definition

**Quality Gate is production-ready when:**

1. ✅ All 10 test scenarios pass with correct decisions
2. ✅ Spec Engineer detects all 4 drift types (0% false positives)
3. ✅ Cost baseline verified at $0.31/commit
4. ✅ Latency < 30 sec for parallel execution
5. ✅ Lead Engineer + Principal Engineer sign off
6. ✅ Documentation complete (runbook, integration guide, reports)

**Status**: READY FOR PHASE 6 TESTING
