# URGENT: Critical Issues Checklist
**Date:** 2026-05-30  
**Status:** Needs Immediate Action  

## 🔴 BLOCKER #1: 10 Test Failures (2 hours to fix)

### Issue
Tests hardcode model constants that don't include `claude-opus-4.8`, which is now in the locked models list.

### Failing Tests (10 total)
- ❌ tests/test_model_naming_compliance.py::TestModelNamingCompliance::test_agent_files_use_locked_models
- ❌ tests/test_model_naming_compliance.py::TestModelNamingCompliance::test_agent_files_use_hyphen_format
- ❌ tests/test_model_naming_compliance.py::TestModelNamingConsistency::test_agent_files_match_validator
- ❌ tests/claude/test_agent_verifier.py::TestStartupChecker::test_startup_checker_init (intermittent)
- ❌ tests/claude/test_agent_verifier.py::TestIntegration::test_initialize_harness_check_success (intermittent)
- ❌ tests/standardization/test_skill_standardizer.py::TestFrontmatterParsing::test_parse_valid_frontmatter (intermittent)
- ❌ tests/standardization/test_skill_standardizer.py::TestFrontmatterParsing::test_parse_invalid_frontmatter (intermittent)
- ❌ tests/standardization/test_skill_standardizer.py::TestFrontmatterParsing::test_parse_no_frontmatter (intermittent)
- ❌ tests/standardization/test_skill_standardizer.py::TestDocumentStructure::test_extract_sections (intermittent)
- ❌ tests/standardization/test_skill_standardizer.py::TestAuditReportGeneration::test_compliance_report_generation (intermittent)

### Root Cause
```
security-engineer-agent.md uses: model: claude-opus-4.8
.githooks/LOCKED_MODELS.sh has: claude-opus-4.8 in locked set ✓

BUT test files have hardcoded constants that DON'T include claude-opus-4.8:
  tests/test_model_naming_compliance.py line 50-55:
    LOCKED_MODELS = {
        "claude-haiku-4.5",
        "claude-sonnet-4.5",
        "claude-sonnet-4.6",
        "claude-opus-4.6",
        "claude-opus-4.7",    ← Missing: claude-opus-4.8
    }
```

### Fix Required

#### File 1: tests/test_model_naming_compliance.py (Line 50-66)
```python
# BEFORE (BROKEN)
LOCKED_MODELS = {
    "claude-haiku-4.5",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.6",
    "claude-opus-4.7",
}

APPROVED_MODELS = {
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
}

# AFTER (FIXED)
LOCKED_MODELS = {
    "claude-haiku-4.5",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",      ← ADD THIS
}

APPROVED_MODELS = {
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",      ← ADD THIS
}
```

#### File 2: renderer/validate_agents.py
Find the KNOWN_MODELS set and add `"claude-opus-4.8"`:
```python
KNOWN_MODELS = {
    "claude-haiku-4.5",
    "claude-haiku-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-opus-4.8",      ← ADD THIS
}
```

### Verification Steps
```bash
# 1. Make edits above
# 2. Run test suite
cd /Users/niall/git/agentic-engineers
python3 -m pytest tests/test_model_naming_compliance.py -v
  # Expected: 15 passed (was 12 passed, 3 failed)

# 3. Run full suite
python3 -m pytest --tb=no -q
  # Expected: 4,281 passed (was 4,271 passed, 10 failed)

# 4. Create PR and merge
git add -A
git commit -m "fix: add claude-opus-4.8 to model version constants"
git push
```

### Effort: 2 hours (15 min coding + 45 min testing + 30 min PR/review)

---

## 🟡 BLOCKER #2: Unmerged Feature Branches (Needs Triage)

### Branches with Unmerged Changes
```
feature/TASK-SECURITY-ANALYSIS-GAPS-001 ........... 4 commits ahead
feature/TASK-LINTING-GATES-001 .................... 1 commit ahead
feature/TASK-QUEUE-PROTOCOL-INTEGRATION-001 ...... 1 commit ahead
feature/TASK-CI-PATH-SYMLINK-IMPL-001 ............ ? unknown
feature/TASK-SESSION-MEMORY-ARTIFACTS-001 ....... ? unknown
feature/TASK-TEST-ENVIRONMENT-SIMULATION-001 .... ? unknown
feature/spec-audit-phase1-5-security-hardening .. ? unknown
feature/spec-audit-phase1-security-assessment .... ? unknown
fix/ci-path-validation-and-symlinks .............. ? unknown
```

### Action Required
- [ ] Review each branch
- [ ] Decide: merge, close, or keep WIP
- [ ] Document decision
- [ ] Clean up stale branches

### Owner: Tech Lead / Orchestrator

---

## 🟠 BLOCKER #3: Milestone 2 & 3 Pending (15 days to Feature Freeze)

### Milestone 2: Harness Stability (2-3 weeks, due 2026-06-13)
```
[CRITICAL - START NOW]
- [ ] OPENCODE-QUEUE-PATH-DETECTION (2-3 hrs) → Engineer
- [ ] OPENCODE-HARNESS-CHECKER (1-2 hrs) → Quality Engineer
- [ ] OPENCODE-RUNNER-INTEGRATION (2-3 hrs) → Senior Engineer
- [ ] CLAUDE-AGENT-AVAILABILITY (2-3 hrs) → Quality Engineer
- [ ] CLAUDE-SKILL-RENDERING (2-3 hrs) → Quality Engineer
- [ ] COPILOT-MODEL-ROUTING (2-3 hrs) → Model Engineer
- [ ] COPILOT-TOKEN-TRACKING (2-3 hrs) → Model Engineer

TOTAL EFFORT: 15-20 hours
CRITICAL PATH: OPENCODE tasks block framework usage
DEADLINE: 2026-06-13 (before feature freeze)
```

### Milestone 3: Skills Audit & Consolidation (ongoing, due 2026-06-13)
```
[HIGH - PARALLEL WITH M2]
- [ ] SKILLS-AUDIT (2-3 hrs) → Lead Engineer
- [ ] SKILLS-STANDARDIZATION (3-5 hrs) → Quality Engineer
- [ ] Deprecated Skills Review (1-2 hrs) → Senior Engineer

TOTAL EFFORT: 6-12 hours
RECOMMENDATION: All 19 skills need test coverage ≥85% (currently 3/10 avg)
DEADLINE: 2026-06-13 (before feature freeze)
```

### Post-Merge: EVALS Framework (CRITICAL)
```
[CRITICAL - UNBLOCKS HARNESS TESTING]
- [ ] EVALS-INFRASTRUCTURE (8 hours) → Senior Engineer
- [ ] EVALS-001: Harness Integration Tests (2-3 weeks)
- [ ] EVALS-002: Model Compatibility Matrix (1-2 weeks)
- [ ] EVALS-003: Skill Interoperability Tests (1-2 weeks)
- [ ] EVALS-004: End-to-End Workflows (2-3 weeks)
- [ ] EVALS-005: Continuous CI/CD Pipeline (1-2 weeks)

TOTAL EFFORT: 20-30 hours
BLOCKS: Cannot validate harness compatibility without this
DEADLINE: 2026-06-15 (feature freeze - hard stop)
```

---

## 📋 TODO: This Week (2026-06-02 to 2026-06-06)

### PRIORITY 1: Test Failures (TODAY)
- [ ] Update model constants in 2 test files
- [ ] Run pytest to verify 4,281 passing
- [ ] Create PR `fix: claude-opus-4.8 model version update`
- [ ] Merge to main
- **Effort:** 2 hours | **Owner:** Quality Engineer

### PRIORITY 2: Harness Tasks (Days 2-5)
- [ ] OPENCODE-QUEUE-PATH-DETECTION implementation (3 hours)
- [ ] OPENCODE-HARNESS-CHECKER implementation (2 hours)
- [ ] OPENCODE-RUNNER-INTEGRATION implementation (3 hours)
- [ ] CLAUDE-AGENT-AVAILABILITY implementation (3 hours)
- **Effort:** 11 hours | **Owners:** Engineer, Quality Engineers

### PRIORITY 3: EVALS Infrastructure (Days 4-7)
- [ ] EVALS-INFRASTRUCTURE framework implementation (8 hours)
- [ ] Write test case format spec
- [ ] Implement TestRunner, reporters, result persistence
- [ ] Integration with CI/CD
- **Effort:** 8 hours | **Owner:** Senior Engineer

### PRIORITY 4: Branch Cleanup (Days 3-5)
- [ ] Review all 8 unmerged feature branches
- [ ] Decide: merge, close, or keep
- [ ] Document decisions
- [ ] Clean up stale branches
- **Effort:** 2 hours | **Owner:** Tech Lead

---

## 🎯 Success Criteria

### By End of Week 1 (2026-06-06)
- ✅ All 10 test failures resolved (pass rate 100%)
- ✅ OPENCODE harness tasks implemented (3/7)
- ✅ EVALS infrastructure ready for use
- ✅ Feature branches triaged and documented

### By Feature Freeze (2026-06-15)
- ✅ Milestone 2 complete (7/7 tasks)
- ✅ Milestone 3 complete (3/3 tasks)
- ✅ All EVALS tests implemented
- ✅ Skills standardization complete
- ✅ Pass rate maintained at 100%

---

## 📊 Risk Scorecard

| Risk | Severity | Likelihood | Mitigation | Owner |
|------|----------|-----------|-----------|-------|
| Test failures block CI | HIGH | TODAY | Fix in 2 hrs | QE |
| Feature freeze miss | MEDIUM | MEDIUM | Start NOW | Tech Lead |
| Silent harness failures | CRITICAL | HIGH | EVALS framework | QE |
| Skills regressions | HIGH | HIGH | Test coverage | Lead Eng |

---

## 📞 Escalation Path

**For Blockers:**
1. Quality Engineer → Tech Lead (same-day escalation)
2. Tech Lead → Orchestrator (if >2 day blocking)
3. Orchestrator → Steering Committee (if >1 week blocking)

**Current Escalation Status:** YELLOW (test failures need immediate attention)

---

**Last Updated:** 2026-05-30  
**Status:** READY TO ACTION  
**Next Checkpoint:** 2026-06-02 (EOD - verify test fixes complete)
