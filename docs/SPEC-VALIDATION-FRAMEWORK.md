# Spec Validation Framework

**Goal:** Continuously validate that agentic-engineers implementation matches SPEC.md.

**Approach:** Spec Engineer agent evaluates current code against specification, detects drift types, reports gaps.

---

## 1. Spec Drift Types (TYPE_A through TYPE_D)

### TYPE_A: Documented Feature Missing in Code
- **What:** Spec says feature X exists, but it's not in code
- **Examples:** 
  - Spec requires SecurityEngineerAgent, but only 12 agents implemented
  - Spec requires DELEGATE validation, but no input checking
- **Severity:** HIGH (breaking regression)
- **Action:** Implement missing feature

### TYPE_B: Code Feature Undocumented in Spec
- **What:** Code has feature Y, but spec doesn't mention it
- **Examples:**
  - Code has artifact versioning, spec doesn't mention it
  - Code has caching layer, spec doesn't document it
- **Severity:** MEDIUM (API change risk, documentation debt)
- **Action:** Add to spec OR remove from code (intentional vs accidental?)

### TYPE_C: Spec & Code Mismatch
- **What:** Spec and code describe same feature differently
- **Examples:**
  - Spec says Haiku 4.5, code uses Haiku 4.4
  - Spec says "aggregate 5 agents", code aggregates 4
  - Spec says "confidece formula: 0.70 + X", code uses 0.65 + X
- **Severity:** MEDIUM (inconsistent understanding)
- **Action:** Align spec OR align code (which is truth?)

### TYPE_D: Breaking Change Without Deprecation
- **What:** Spec changed incompatibly without migration path
- **Examples:**
  - DELEGATE block changed format (new required field)
  - Routing decision tree changed (old decision paths now invalid)
  - Agent role renamed (external code breaks)
- **Severity:** HIGH (migration hazard)
- **Action:** Implement deprecation period OR revert change

---

## 2. Spec Validation Checklist

**When to validate:** After every significant code change, weekly during implementation

### Architecture Checks
- [ ] **13 agents present:** All SDLC (8) + QG sub (5) agents implemented
- [ ] **Agent models correct:** Each agent uses specified model (Haiku/Sonnet/Opus)
- [ ] **Effort levels correct:** Each agent has correct effort (low/medium/high/max)
- [ ] **Routing tree correct:** Orchestrator follows 6-point decision tree from SPEC.md
- [ ] **QG subsystem present:** All 5 sub-agents + Orchestrator implemented

### Protocol Checks
- [ ] **DELEGATE structure:** All required fields present (task_id, role, model, effort, scope)
- [ ] **HANDBACK structure:** All required fields present (status, severity, confidence)
- [ ] **FEEDBACK structure:** Feedback blocks generated correctly
- [ ] **No external calls:** Zero Claude API calls, shell scripts, external services in agent code

### Feature Checks
- [ ] **Input validation:** Each agent validates DELEGATE block
- [ ] **Error handling:** ValueError for validation errors, RuntimeError for execution errors
- [ ] **Confidence algorithm:** Implemented per SPEC.md Section 5.2
- [ ] **Artifact management:** DELEGATE/HANDBACK written to disk correctly
- [ ] **Feedback loops:** All 3 loops implemented (QG, ME, Config Enforcement)

### Quality Gate Checks
- [ ] **5 sub-agents parallel:** Security, Testing, Metrics, Healing, Spec Engineer
- [ ] **Decision logic:** All PASS → PROCEED; any ESCALATE → ESCALATE
- [ ] **Latency target:** <30 seconds total for all 5 agents in parallel
- [ ] **Accuracy targets:** 0% false positives, <2% false negatives on test scenarios

### Documentation Checks
- [ ] **SPEC.md up-to-date:** All agents, models, efforts documented
- [ ] **README.md accurate:** Architecture, protocol, examples correct
- [ ] **Agent specs complete:** Each of 7 agents has detailed spec
- [ ] **Constraint documented:** "Self-contained, no external dependencies" clear everywhere

---

## 3. Spec Validation Process

### Weekly Validation (1 hour)

1. **Read this week's commits**
   - `git log --oneline -20`
   - Identify spec-relevant changes

2. **Run validation checks**
   ```bash
   python orchestration/agents/spec_validator.py
   ```
   Output: TYPE_A/B/C/D issues found, severity levels, remediation suggestions

3. **For each issue found:**
   - Is it intentional (change approved in SPEC.md)?
   - Or accidental (code diverged from spec)?
   - If intentional: update SPEC.md
   - If accidental: fix code or revert

4. **Update SPEC.md if needed**
   - Document approved changes
   - Update agent configs if models/efforts changed
   - Add notes explaining TYPE_C mismatches

### During Implementation (Daily)

1. **After implementing an agent:**
   ```bash
   python orchestration/agents/spec_validator.py --agent GeneralOrchestrator
   ```
   Confirms agent matches spec

2. **After changing DELEGATE/HANDBACK protocol:**
   ```bash
   python orchestration/agents/spec_validator.py --protocol
   ```
   Confirms all agents still validate correctly

3. **Before running test harness:**
   ```bash
   python orchestration/agents/spec_validator.py --full
   ```
   Full validation, then run tests

---

## 4. Spec Validator Tool (spec_validator.py)

**Purpose:** Automated validation of code against spec.md

**Usage:**
```bash
# Full validation
python orchestration/agents/spec_validator.py

# Validate specific agent
python orchestration/agents/spec_validator.py --agent EngineerAgent

# Validate protocol only
python orchestration/agents/spec_validator.py --protocol

# Verbose output
python orchestration/agents/spec_validator.py --verbose

# Check for TYPE_A/B/C/D drift
python orchestration/agents/spec_validator.py --drift-types
```

**Output:**
```
╔═══════════════════════════════════════════════════════════╗
║  Spec Validation Report                                   ║
╚═══════════════════════════════════════════════════════════╝

Architecture:
  ✅ 13 agents present (8 SDLC + 5 QG)
  ✅ Models correct (Haiku/Sonnet/Opus)
  ✅ Effort levels correct
  ✅ Routing tree matches spec
  ✅ QG subsystem present

Protocol:
  ✅ DELEGATE structure valid
  ✅ HANDBACK structure valid
  ✅ No external dependencies

Features:
  ✅ Input validation present
  ✅ Error handling implemented
  ✅ Confidence algorithm correct
  ✅ Artifact management working
  ✅ Feedback loops implemented

Quality Gate:
  ✅ 5 sub-agents implemented
  ✅ Decision logic correct
  ⚠️  Latency: 35s (target: <30s)
  ✅ Accuracy targets met

TYPE_A Issues (Documented Feature Missing):
  None found ✅

TYPE_B Issues (Code Feature Undocumented):
  1. Artifact versioning (not in spec)
     → Add to SPEC.md or remove from code?

TYPE_C Issues (Spec/Code Mismatch):
  1. SecurityEngineerAgent model: spec=Opus 4.7, code=Opus 4.6
     → Align code to spec (update to 4.7)

TYPE_D Issues (Breaking Change Without Deprecation):
  None found ✅

Summary:
  Valid: 23/25 checks ✅
  Warnings: 1 undocumented feature
  Errors: 1 model version mismatch
  
Recommendation: Fix TYPE_C issue, decide on TYPE_B feature
```

---

## 5. Spec as Source of Truth

**When code and spec disagree:**

1. **SPEC is source of truth** for:
   - Agent models (Haiku/Sonnet/Opus)
   - Effort levels (low/medium/high/max)
   - DELEGATE/HANDBACK structure
   - Routing decision tree
   - Confidence algorithm
   - Agent roles and responsibilities

2. **Code is source of truth** for:
   - Actual implementation patterns
   - Bug fixes discovered during coding
   - Performance optimizations found necessary
   - Edge cases not covered in spec

3. **When they conflict:**
   - If spec is ambiguous/incomplete: implement what makes sense, UPDATE SPEC
   - If spec is clear but code does something else: CHANGE CODE to match spec
   - If spec needs change: update SPEC.md, document rationale, mark as TYPE_C if intentional

---

## 6. Continuous Validation During Implementation

### Week 1: SDLC Agents

After each agent implemented:
```bash
python orchestration/agents/spec_validator.py --agent <AgentName>
```
Should show: 0 TYPE_A/B/C/D issues for that agent

### Week 2: QG Sub-Agents

After QG subsystem complete:
```bash
python orchestration/agents/spec_validator.py --subsystem qg
```
Should show: All 5 agents present, decision logic correct, no drift

### Week 3: Feedback Loops

After feedback loops implemented:
```bash
python orchestration/agents/spec_validator.py --subsystem feedback-loops
```
Should show: All 3 handlers present, chaining works, no external dependencies

### Week 4: Full Validation

Before shipping:
```bash
python orchestration/agents/spec_validator.py --full --strict
```
Should show: 0 TYPE_A/B/C/D issues, all checks pass, latency <30s

---

## 7. Spec Update Process

When you intentionally change something:

1. **Update SPEC.md**
   - Document the change
   - Explain why
   - Mark section as updated with date

2. **Run validator**
   ```bash
   python orchestration/agents/spec_validator.py
   ```
   Confirm change is now documented

3. **Update this document**
   - If it's a new TYPE_C item: document rationale
   - If it's fixing TYPE_A/B/D: note resolution

---

## 8. Example: Detecting TYPE_C Drift

**Scenario:** SecurityEngineerAgent model changes from Opus 4.7 → Opus 4.6

**Step 1: Code changes**
```python
# In implementations.py
SECURITY_ENGINEER_CONFIG = AgentConfig(
    model="claude-opus-4-6",  # Changed from 4.7
    ...
)
```

**Step 2: Spec still says**
```markdown
# Section 3.1: Security Engineer Agent
- Model: claude-opus-4-7
```

**Step 3: Validator detects**
```
TYPE_C Issue: SecurityEngineerAgent model mismatch
  Spec: claude-opus-4-7
  Code: claude-opus-4-6
  Severity: MEDIUM
```

**Step 4: Decision**
- **Option A:** Update spec to 4.6 (code is truth)
  - Document: "Downgraded to 4.6 for cost savings, acceptable accuracy"
- **Option B:** Update code to 4.7 (spec is truth)
  - Revert change, keep higher model

**Step 5: Update spec or code, re-run validator**
```bash
python orchestration/agents/spec_validator.py
# Should show: 0 TYPE_C issues
```

---

## 9. What Gets Enshrined in Spec

✅ **MUST be in spec:**
- All 13 agents (names, models, effort, roles)
- DELEGATE/HANDBACK/FEEDBACK structures
- Routing decision tree
- Confidence algorithm
- Agent responsibilities
- Quality Gate decision logic
- Feedback loop structures

❌ **Should NOT be in spec:**
- Implementation details (how agent X works internally)
- Specific code patterns
- Artifact file formats (YAML vs JSON)
- Performance optimization tricks

---

## Summary

**Spec Validation ensures:**
1. Code matches specification (no accidental drift)
2. Specification is complete (no missing features)
3. Breaking changes are intentional & documented
4. Implementation can be audited against spec
5. Spec can be used to re-implement system

**Run weekly:** `python orchestration/agents/spec_validator.py`  
**Fix any TYPE_A/D issues immediately**  
**Resolve TYPE_B/C issues within the sprint**
