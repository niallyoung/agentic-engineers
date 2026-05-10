---
name: Quality Gates Quick Reference
description: Quick reference guide for developers using quality gates
type: developer-guide
---

# Quality Gates — Quick Reference Guide

**TL;DR**: Quality gates ensure code is tested, secure, and compliant before deployment.

---

## Local Development

### Check code before pushing

```bash
# Quick quality check (dev, ~30 seconds)
make quality-gate

# Full quality check (prod-like, ~2 minutes)
make quality-gate-full

# Both must exit with code 0 (success)
# Exit code 1 means issues found → escalate or fix
```

### What Gets Checked?

**Dev Environment** (`make quality-gate`):
- ✅ Unit tests pass
- ✅ E2E tests pass (optional, can skip)
- ⏭️ Security scanning reduced (faster)
- ⏭️ Compliance checks reduced

**Prod Environment** (`make quality-gate-full`):
- ✅ Unit tests pass
- ✅ E2E tests pass (required for prod)
- ✅ No hardcoded secrets
- ✅ No dependency vulnerabilities
- ✅ Requirements traceability complete
- ✅ Spec compliance verified

---

## Common Workflows

### Workflow 1: Normal Development

```bash
# 1. Edit code
vim lambda/command-gateway/handlers.go

# 2. Commit locally (pre-commit hook runs lint + test)
git commit -m "feat: add new command handler"

# 3. Run quality gates (optional but recommended)
make quality-gate

# 4. If quality-gate passes, push to main
git push

# 5. GitHub Actions runs full quality-gate-prod job
# 6. If quality gates pass, automatic prod deployment ✅
```

### Workflow 2: Issue Found by Quality Gates

```bash
# Run quality gates and see what failed
make quality-gate-full

# Output:
# ❌ Unit tests: FAIL
# ❌ E2E tests: PASS
# ✅ Security: PASS

# For test failures:
go test ./... -v -run TestFailingName  # Debug locally

# Fix the issue
# vim lambda/command-gateway/handlers_test.go

# Re-run quality gates
make quality-gate-full  # Should now pass ✅

git push
```

### Workflow 3: GitHub Actions Quality Gate Fails

You pushed, but quality gates failed in GitHub Actions (quality-gate-prod job):

```bash
# 1. Check GitHub Actions logs:
#    https://github.com/{your-org}/{example-service}/actions

# 2. Find the quality-gate-prod job output
#    Look for Phase 1, Phase 2, Phase 4 results

# 3. Fix locally and re-push
git pull origin main
# Fix the issue
make quality-gate-full  # Verify locally before pushing

git commit -am "fix: resolve quality gate failure"
git push
```

**Important**: GitHub Actions will automatically re-run. No need to manually trigger.

---

## Quality Gate Decisions

### PROCEED ✅
All checks passed. Code is ready for production.
- Unit tests: PASS
- E2E tests: PASS
- Security: PASS
- Compliance: PASS
- **Action**: Deployment continues to prod

### WARN ⚠️
Some checks found issues, but they might be fixable.
- Tests: FAIL (but fixable, e.g., flaky)
- Security: WARN (minor issue, escalate for review)
- **Action**: Escalate to Lead Engineer for manual decision

### BLOCK 🛑
Critical issues found, code cannot be deployed.
- Tests: FAIL (multiple failures)
- Security: FAIL (vulnerability detected)
- **Action**: Fix locally, re-test, re-push

### ESCALATE 🆘
High-risk issues found requiring human judgment.
- Logic bug (not auto-fixable)
- Security vulnerability (requires expert review)
- Architecture change needed
- **Action**: Escalate to appropriate team (Lead/Security/Principal)

---

## Troubleshooting

### "make quality-gate: command not found"
Quality gate script not in PATH. Make sure you're in the service directory:
```bash
cd $WORKSPACE_ROOT/{example-service}
make quality-gate  # Should work now
```

### "quality-gate FAIL but make test passes"
Different scripts/tools might be running. Quality gate runs additional checks:
```bash
# Quality gate does: lint + unit tests + E2E + security + compliance
# make test does: only unit tests

# Run the full check:
make quality-gate-full
```

### "How do I skip E2E tests?"
Use the quick check (skip E2E):
```bash
make quality-gate    # Skips E2E tests (~30s)
make quality-gate-full  # Includes E2E tests (~2 min)
```

### "GitHub Actions quality-gate-prod blocked deployment"
1. Check the job logs: GitHub Actions → main workflow → quality-gate-prod
2. Find the specific failure in Phase 1/2/4 output
3. Fix locally and push again
4. GitHub Actions will automatically re-run

### "How do I force-skip quality gates?"
**Not recommended**, but possible:
```bash
git push --no-verify  # Skips local quality checks

# BUT: GitHub Actions quality-gate-prod will still run
# If you push bad code, GitHub Actions will block deployment
# Better to fix locally than push and wait for CI to reject
```

---

## Phase 3: Self-Healing (Coming Soon)

**What It Does**:
- Detects issues (tests fail, security warning, config missing)
- Diagnoses root cause
- Auto-fixes if safe (missing env var, flaky test)
- Creates PR with fix
- Re-runs quality gates on the PR

**Healer Will Fix Automatically**:
- ✅ Missing environment variable
- ✅ Flaky test (add retry logic)
- ✅ Dependency patch update (1.2.5 → 1.2.6)
- ✅ Import path wrong
- ✅ Lockfile stale

**Healer Will NOT Fix** (escalates to human):
- ❌ Logic bug (code review needed)
- ❌ Security vulnerability (security expert needed)
- ❌ Architecture change (design decision needed)
- ❌ Major dependency update (compatibility testing needed)

**What To Expect**:
- Healer creates PR with fix
- Runs quality gates on the PR
- If all gates pass, optionally auto-merges
- You'll get notified in Slack about the auto-fix

---

## Best Practices

### Do's ✅
- [x] Run `make quality-gate` before pushing
- [x] Read GitHub Actions logs when deployment blocks
- [x] Fix issues locally and re-push
- [x] Use `make quality-gate-full` for prod-ready code
- [x] Review Healer PRs before auto-merge (when available)

### Don'ts ❌
- [ ] Don't push without testing locally
- [ ] Don't ignore quality gate failures
- [ ] Don't repeatedly `git push --no-verify`
- [ ] Don't commit hardcoded secrets/API keys
- [ ] Don't edit quality gate script without approval

---

## Audit Trail

Quality gates generate an audit log showing what was checked:

```bash
$ ls quality-gate-audit-*.jsonl
quality-gate-audit-8d6d9fa0-ff5.jsonl

$ cat quality-gate-audit-8d6d9fa0-ff5.jsonl
{"timestamp":"2026-04-28T04:35:11Z","session_id":"8d6d9fa0-ff5","phase":"phase_1","status":"COMPLETE","details":{...}}
{"timestamp":"2026-04-28T04:35:11Z","session_id":"8d6d9fa0-ff5","phase":"phase_2","status":"PROCEED","details":{...}}
{"timestamp":"2026-04-28T04:35:11Z","session_id":"8d6d9fa0-ff5","phase":"phase_4","status":"PROCEED","details":{...}}
```

**Use For**:
- Compliance auditing (who deployed when)
- Debugging (why did deployment block)
- Metrics (how many issues per week)
- Continuous improvement (common failure patterns)

---

## Questions?

**Issue with quality gates?**
→ File an issue in `agentic-engineers` repo

**Want to understand quality gates better?**
→ Read `PHASE-5-INTEGRATION-GUIDE.md`

**Need to override quality gates?**
→ Talk to Lead Engineer (only in emergencies)

**Want to contribute improvements?**
→ See `PHASE-5-INTEGRATION-GUIDE.md` for extension points

---

**Version**: 1.0  
**Last Updated**: 2026-04-28  
**Status**: Ready for all 8 ERS services
