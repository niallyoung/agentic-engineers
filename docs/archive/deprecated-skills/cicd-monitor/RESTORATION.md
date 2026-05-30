# cicd-monitor Restoration Guide

## Status

**Deprecated:** 2026-05-30  
**Reason:** Low maintenance priority, no test coverage, minimal implementation. Better served by GitHub Actions native workflows and the consistent-checker skill for post-push validation.

## Deprecation Rationale

- **No test coverage** — complex CI/CD integration without validation
- **Minimal implementation** — only 1 primary script despite broad scope (4 phases)
- **Functional overlap** — GitHub Actions workflows already provide CI monitoring; consistency-checker provides protocol validation
- **Low priority category** — monitoring is lower priority than core validation and queue management
- **Unclear value** — no telemetry showing actual usage or adoption

## Historical Context

`cicd-monitor` was designed to continuously monitor CI/CD pipeline health by:

1. **Monitor phase** — Fetch workflow runs every 3-5 minutes, identify failures
2. **Analysis phase** — Parse logs, categorize errors (build, test, lint, deploy)
3. **Escalation phase** — Route to appropriate specialist (Senior Engineer, QE, Security, etc.)
4. **Retry phase** — Create DELEGATEs with fixes, auto-retry with 3-5 minute intervals

However, GitHub Actions already provides comprehensive CI/CD monitoring via:
- Workflow notifications (Slack, email, GitHub notifications)
- Native status checks on pull requests
- Workflow status badges on README
- GitHub Actions dashboard with detailed logs

The `consistency-checker` skill already handles post-push validation of DELEGATE/HANDBACK protocol compliance, which is the primary concern for this framework.

## Alternatives & Migration Paths

**For CI/CD monitoring, use one of these alternatives:**

1. **GitHub Actions workflows** (RECOMMENDED)
   - Use `.github/workflows/ci.yml` for standard CI pipeline
   - Use `.github/workflows/on_failure_notify.yml` for failure notifications
   - Use branch protection rules for required status checks
   - This is the standard approach and well-supported by GitHub

2. **consistency-checker skill** (FOR PROTOCOL VALIDATION)
   - Already provides post-push validation of DELEGATE/HANDBACK files
   - Detects cycle violations, rate limit issues, schema compliance
   - Runs on every push automatically via `make pre-push` hook
   - This is the framework-specific validation we need

3. **GitHub Issues/Projects** (FOR FAILURE TRACKING)
   - Use GitHub Issues to track CI failures manually
   - Use GitHub Projects for triage and prioritization
   - Link Issues to PRs for context
   - Simpler and more transparent than automated escalation

4. **Third-party CI monitoring** (FOR ADVANCED MONITORING)
   - Tools like Datadog, New Relic, or CloudWatch
   - Better instrumentation and alerting
   - Integrate with PagerDuty for on-call routing
   - For teams requiring SLA compliance

## When to Restore

**Do NOT restore this skill unless:**
1. You need framework-specific (not GitHub Actions-native) CI monitoring
2. Custom escalation logic is required beyond GitHub's native workflows
3. Comprehensive test suite is added (≥15 tests covering all 4 phases)
4. Clear metrics show actual usage and value

**Restore if:** Your team needs sophisticated custom CI/CD orchestration beyond what GitHub Actions provides natively.

## Git Commands to Restore

**Option A: Restore from archive (this repository)**
```bash
# Copy the archived skill back to active skills
cp -r docs/archive/deprecated-skills/cicd-monitor ~/.claude/skills/cicd-monitor

# Update __init__.py to re-enable
# Edit .opencode/agent-router.yaml to include cicd-monitor in routing

# Add comprehensive test suite
pytest tests/test_cicd_monitor.py -v

# Commit and push
git add -A
git commit -m "restore: re-enable cicd-monitor skill with test suite"
git push
```

**Option B: Restore from git history**
```bash
git log --oneline --all -- .claude/skills/cicd-monitor | head -5
git show <commit_hash>:.claude/skills/cicd-monitor > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/cicd-monitor
# Re-run tests and commit
```

## How to Re-Enable

**BEFORE re-enabling, address all deprecation concerns:**

1. **Add comprehensive test suite:**
   ```bash
   tests/test_cicd_monitor.py (minimum 15 tests)
   - test_detect_workflow_failure
   - test_parse_build_error_log
   - test_categorize_error_type
   - test_escalate_to_senior_engineer
   - test_escalate_to_quality_engineer
   - test_escalate_to_security_engineer
   - test_create_retry_delegate
   - test_retry_after_fix
   - test_escalate_after_3_failed_retries
   - test_integration_with_consistency_checker
   + 5 more
   ```

2. **Document GitHub Actions integration:**
   - Clarify how cicd-monitor complements GitHub Actions
   - Define when to use native GitHub Actions vs. custom monitoring
   - Add examples in docs/

3. **Re-register in __init__.py:**
   ```python
   from .cicd_monitor import CICDMonitor
   AVAILABLE_SKILLS['cicd-monitor'] = CICDMonitor
   ```

4. **Update routing rules:**
   ```yaml
   - skill: cicd-monitor
     condition: "event == 'workflow_failure' AND auto_escalate == true"
     role: orchestrator
     tier: lightweight
   ```

5. **Update docs/SKILLS-AVAILABLE.md:**
   - Move from "Deprecated" section back to "Operations Skills"

6. **Commit:**
   ```bash
   git add tests/ skills/ .opencode/ docs/
   git commit -m "restore: re-enable cicd-monitor with test suite and integration docs"
   make verify
   git push
   ```

## Archive Location

```
docs/archive/deprecated-skills/cicd-monitor/
├── SKILL.md (original skill definition)
├── scripts/ (original implementation)
├── RESTORATION.md (this file)
└── tests/ (original tests, if any)
```

## Last Known State

- **Deprecation Commit:** d84e255e (2026-05-30)
- **Test Coverage:** 0% (no tests in original)
- **Scripts:** 1 primary implementation file
- **Category:** monitoring

## Questions?

Refer to:
- `docs/DEPRECATED-SKILLS.md` — Master index
- `.github/workflows/ci.yml` — Native CI/CD configuration
- `docs/consistency-checker.md` — Protocol validation alternative
