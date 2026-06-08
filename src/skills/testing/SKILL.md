---
name: testing
description: Validates test fixture synchronization with code changes. Detects orphaned test expectations, stale fixtures, and missing test coverage for code updates. Use as pre-merge gate to catch test-code drift before regressions reach CI.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: testing
  role: quality-engineer
  model: claude-haiku-4.5
  effort: medium
  thinking: false
  trigger: pre-merge | post-merge-audit
---

## Overview

Test-Sync-Validator prevents test-code drift by catching three critical failure patterns:

1. **Orphaned Expectations** — Test fixtures reference code values that no longer exist (e.g., hardcoded model names, removed config keys)
2. **Stale Fixtures** — Test data hasn't been updated after code refactors (e.g., renamed classes, moved files, changed APIs)
3. **Missing Coverage** — Code changes (new models, config updates, API changes) lack corresponding test fixture updates

**What it does:**

- Analyzes git diffs to identify code changes (code/config/docs)
- Cross-references test fixtures for synchronization
- Detects mismatches: hardcoded values, removed references, changed APIs
- Generates pre-merge reports with:
  - List of affected test files
  - Orphaned fixture values
  - Recommended fixture updates
  - Severity (blocker/high/medium)
- Acts as CI gate: fail merge if critical mismatches detected

**Why it matters:**

- **Prevents Post-Merge Regressions** — Catches test drift before merge (not post-merge in CI)
- **Reduces Manual Test Review** — Automated diff analysis flags suspicious changes
- **Enforces Fixture Freshness** — Ensures test values reflect current code state
- **Improves CI Signal** — CI runs against correct test expectations, not stale ones

---

## Invocation

### Pre-Merge Gate (CI/CD)

```bash
# Fail merge if test fixtures are stale
git diff origin/main...HEAD > /tmp/changes.diff
python scripts/test_sync_validator.py \
  --diff /tmp/changes.diff \
  --mode pre-merge \
  --fail-on-critical
# Exit code: 0 = all fixtures synced, 1 = critical mismatches, 2 = error
```

### Manual Audit Mode

```bash
# Generate report without failing
python scripts/test_sync_validator.py \
  --diff /tmp/changes.diff \
  --mode audit \
  --format json \
  --output artifacts/test-sync-report.json
```

### CI/CD Pipeline Integration

```yaml
# .github/workflows/test-sync-gate.yml
- name: Validate test fixture sync
  run: |
    python src/skills/testing/scripts/test_sync_validator.py \
      --branch ${{ github.head_ref }} \
      --mode pre-merge \
      --fail-on-critical
```

---

## How It Works

### 1. Code Change Detection

Analyzes git diff to find:
- **Source changes** — Modified Python files, config updates, API changes
- **Test changes** — Modified test files and fixtures
- **Documentation changes** — Updated SKILL.md, agent configs, etc.

### 2. Cross-Reference Analysis

For each code change, checks if corresponding test fixtures exist:
- Model updates → test_model_naming_compliance.py (LOCKED_MODELS, APPROVED_MODELS)
- Config changes → renderer/validate_*.py (validation sets)
- API changes → test files (expectations, parameters)
- Router logic → test_cost_aware_router.py (routing expectations)

### 3. Mismatch Detection

Identifies three categories of drift:

**Orphaned Values** (fixture references deleted code):
```
❌ test_model_naming_compliance.py line 54:
   Expected: LOCKED_MODELS = {"claude-opus-4.6", "claude-opus-4.7"}
   Found in code: src/agents/security-engineer-agent.md uses "claude-opus-4.8"
   Status: MISSING - fixture not updated after code upgrade
```

**Stale Expectations** (hardcoded test values don't match current code):
```
❌ test_cost_aware_router.py line 115:
   Expected model: "opus-4-7"
   Current code expects: "opus-4-8"
   Status: OUTDATED - hardcoded expectation not synced with code change
```

**Missing Coverage** (code changed, tests unchanged):
```
⚠️  src/orchestration/cost/cost_aware_router.py line 41:
   Added: "opus-4-8": 3.00 to MODEL_COST_MULTIPLIERS
   Test impact: test_model_selection.py may need quality/cost threshold updates
   Status: NEEDS_REVIEW - verify if test expectations still valid
```

### 4. Report Generation

Produces JSON report with structure:
```json
{
  "total_changes": 15,
  "code_changes": [
    {
      "file": "src/agents/security-engineer-agent.md",
      "change_type": "model_upgrade",
      "before": "claude-opus-4.7",
      "after": "claude-opus-4.8",
      "test_impact": [
        {
          "test_file": "tests/test_model_naming_compliance.py",
          "line": 54,
          "type": "orphaned_value",
          "severity": "critical",
          "message": "LOCKED_MODELS missing claude-opus-4.8"
        }
      ]
    }
  ],
  "summary": {
    "critical_mismatches": 3,
    "high_mismatches": 2,
    "medium_mismatches": 0,
    "pass": false
  }
}
```

---

## Integration Checklist

- [ ] Add `test-sync-validator.py` to `.github/workflows/test-sync-gate.yml`
- [ ] Configure as **blocking gate** on pull requests (fail merge if critical mismatches)
- [ ] Configure as **audit only** on main (report mismatches, don't fail)
- [ ] Update CI/CD to run before `pytest` (catch drift before test execution)
- [ ] Document in CONTRIBUTING.md: "Test fixtures must be kept in sync with code changes"
- [ ] Add pre-commit hook (optional) to warn about potential drift locally

---

## Common Patterns

### Pattern 1: Model Upgrades

**Code change:**
```markdown
# src/agents/security-engineer-agent.md
model: claude-opus-4.8
```

**Expected test updates:**
```python
# tests/test_model_naming_compliance.py
LOCKED_MODELS = {..., "claude-opus-4.8"}
APPROVED_MODELS = {..., "claude-opus-4.8"}

# renderer/validate_agents.py
KNOWN_MODELS = {..., "claude-opus-4.8"}

# tests/test_cost_aware_router.py
# Update security_sensitive test expectation from opus-4-7 to opus-4-8

# tests/test_model_selection.py
# Verify cost/quality tier calculations still valid
```

### Pattern 2: Config Changes

**Code change:**
```python
# src/config/models.yaml
MODEL_COST_MULTIPLIERS = {
    "opus-4-8": 3.50  # Updated from 3.00
}
```

**Expected test updates:**
```python
# tests/test_model_selection.py
# Update cost tier calculations
# Verify downgrade/upgrade recommendations still accurate
```

### Pattern 3: API Signature Changes

**Code change:**
```python
# src/orchestration/cost/cost_aware_router.py
def route_to_model(quality_requirement: float, budget_limit: float) -> str:
    # Added budget_limit parameter
```

**Expected test updates:**
```python
# tests/test_cost_aware_router.py
# Update all test calls to include budget_limit parameter
# Verify routing logic respects budget constraints
```

---

## Failure Cases & Recovery

### Critical Mismatch (Fail Merge)
- Fixture references deleted code (orphaned value)
- Hardcoded expectation conflicts with current code
- New code tier/model/tier needs test coverage

**Recovery:**
```bash
# Fix the test fixture
git add tests/test_file.py
git commit -m "fix: sync test fixture with code change"
git push

# Re-run validator
python scripts/test_sync_validator.py --branch HEAD --mode pre-merge
```

### High Mismatch (Warn, Allow Merge)
- Config change may affect test thresholds
- API parameter added but backward-compatible
- Documentation updated but test expectations unclear

**Recovery:**
```bash
# Review and decide:
# Option A: Update test to verify new behavior
# Option B: Document why test doesn't need changes
git add tests/test_file.py  # or docs/CONTRIBUTING.md
git commit -m "docs: document test fixture expectations for {change}"
```

### Medium Mismatch (Info Only)
- Refactoring with no behavior change
- Comment/docstring updates
- Non-critical config changes

**No action needed** — validator allows automatic merge.

---

## Files

- `scripts/test_sync_validator.py` — Core validation logic
- `scripts/analyzers/code_change_detector.py` — Parse git diffs
- `scripts/analyzers/fixture_cross_referencer.py` — Map code to tests
- `scripts/reporters/mismatch_reporter.py` — Generate reports

See `references/REFERENCE.md` for API details and extension points.
