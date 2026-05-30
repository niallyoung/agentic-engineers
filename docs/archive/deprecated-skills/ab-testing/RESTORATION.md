# ab-testing Restoration Guide

## Status

**Deprecated:** 2026-05-30  
**Reason:** Low maintenance priority, no test coverage, minimal implementation. Core experimentation can be achieved through simpler routing without dedicated skill.

## Deprecation Rationale

- **No test coverage** — experimentation framework without validation
- **Minimal implementation** — only 1 script despite Welch's t-test and early stopping requirements
- **Underutilized** — no evidence of active usage in model selection or routing optimization
- **Functional overlap** — model-engineer skill and orchestrator routing provide similar capabilities
- **Low priority category** — optimization is lower priority than core quality and validation

## Historical Context

`ab-testing` was designed to support experiment orchestration with:
- Traffic allocation to different model variants
- Statistical analysis using Welch's t-test
- Early stopping detection
- Testing of routing changes and model upgrades

However, in practice:
- Model selection can be done through `model-engineer` skill analysis
- A/B testing of routes can be managed through explicit routing logic in orchestrator
- Statistical significance is handled via QE feedback scores
- Experimentation is typically manual and controlled (not continuous)

## Alternatives & Migration Paths

**For A/B testing and experimentation, use one of these alternatives:**

1. **model-engineer skill** (RECOMMENDED)
   - Analyzes quality/cost feedback from QE
   - Recommends optimal model/effort combinations
   - Provides confidence scores for recommendations
   - Better integrated with DELEGATE/HANDBACK protocol

2. **Manual routing via orchestrator** (SIMPLE APPROACH)
   - Define explicit routing rules in `.opencode/agent-router.yaml`
   - Toggle between models by updating config
   - Use git history to track experimental changes
   - Simple, transparent, auditable

3. **GitHub experiments integration** (ADVANCED)
   - GitHub Experiments feature (currently in beta)
   - Native GitHub Actions integration
   - Statistical analysis built-in
   - Better for testing workflow changes

4. **External A/B testing tools** (FOR COMPLEX SCENARIOS)
   - LaunchDarkly for feature flagging with A/B testing
   - Optimizely for sophisticated experimentation
   - Statsmodels Python library for custom statistical analysis
   - For teams requiring enterprise-grade experimentation

## When to Restore

**Do NOT restore this skill unless:**
1. Sophisticated continuous A/B testing is required across many model variants
2. Statistically rigorous experimentation with early stopping is needed
3. Comprehensive test suite is added (≥15 tests for Welch's t-test, early stopping)
4. Clear metrics show adoption and value

**Restore if:** Your organization runs continuous A/B tests across model selections and needs automated statistical analysis.

## Git Commands to Restore

**Option A: Restore from archive**
```bash
cp -r docs/archive/deprecated-skills/ab-testing ~/.claude/skills/ab-testing
# Update __init__.py to re-enable
pytest tests/test_ab_testing.py -v
git add -A
git commit -m "restore: re-enable ab-testing with comprehensive tests"
git push
```

**Option B: Restore from git history**
```bash
git log --oneline --all -- .claude/skills/ab-testing | head -5
git show <commit_hash>:.claude/skills/ab-testing > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/ab-testing
```

## How to Re-Enable

**BEFORE re-enabling, address deprecation concerns:**

1. **Add comprehensive test suite:**
   ```bash
   tests/test_ab_testing.py (minimum 15 tests)
   - test_allocate_traffic_by_percentage
   - test_welch_t_test_calculation
   - test_calculate_p_value
   - test_detect_statistical_significance
   - test_early_stopping_condition
   - test_confidence_interval_calculation
   - test_sample_size_requirement
   - test_result_aggregation
   - test_handle_insufficient_samples
   - test_track_metrics_for_variants
   + 5 more
   ```

2. **Re-register in __init__.py:**
   ```python
   from .ab_testing import ABTesting
   AVAILABLE_SKILLS['ab-testing'] = ABTesting
   ```

3. **Update routing rules:**
   ```yaml
   - skill: ab-testing
     condition: "experiment_mode == 'enabled' AND variants.count > 1"
     role: model-engineer
     tier: standard
   ```

4. **Update docs/SKILLS-AVAILABLE.md**

5. **Commit:**
   ```bash
   git add tests/ skills/ .opencode/ docs/
   git commit -m "restore: re-enable ab-testing with comprehensive Welch's t-test suite"
   make verify
   git push
   ```

## Archive Location

```
docs/archive/deprecated-skills/ab-testing/
├── SKILL.md (original skill definition)
├── scripts/ (original implementation)
├── RESTORATION.md (this file)
└── tests/ (original tests, if any)
```

## Last Known State

- **Deprecation Commit:** d84e255e (2026-05-30)
- **Test Coverage:** 0% (no tests in original)
- **Scripts:** 1 implementation file
- **Category:** optimization

## Questions?

Refer to:
- `docs/DEPRECATED-SKILLS.md` — Master index
- `docs/SKILLS-AVAILABLE.md` → model-engineer skill (preferred alternative)
- `.opencode/agent-router.yaml` — Routing configuration
