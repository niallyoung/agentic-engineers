---
name: Git Hook Bypass Procedures
description: Comprehensive guide to emergency bypass procedures, authorization, and post-bypass recovery
version: 1.0
updated: 2026-05-16
status: Production Ready
---

# Git Hook Bypass Procedures

**Last Updated:** 2026-05-16  
**Scope:** Emergency bypass procedures, authorization requirements, and post-bypass recovery  
**Status:** Production Ready — All bypass methods documented with audit trail requirements

---

## Overview

Git hooks enforce SPEC.md and quality gates. Bypassing hooks should be **rare** and **documented**. This guide covers:

1. **When bypass is appropriate** (genuine emergencies only)
2. **When bypass is NOT appropriate** (lazy commits, avoiding review)
3. **All bypass methods** with examples
4. **Required documentation** for each bypass
5. **Post-bypass recovery** (how to fix root cause)
6. **Audit trail** (how bypasses are tracked)
7. **Authorization** (who can approve bypass)

---

## When Bypass Is Appropriate

### ✅ Genuine Emergencies

**Production Outage**
- Service is down or degraded
- Immediate fix required to restore functionality
- Bypass allows faster deployment
- Example: Database connection pool exhausted

**Critical Security Vulnerability**
- Active security threat
- Immediate patch required
- Bypass allows faster deployment
- Example: SQL injection vulnerability in production

**CI/CD Failure Blocking Team**
- Build pipeline broken
- Team cannot merge code
- Temporary workaround needed
- Example: Test environment misconfiguration

**Temporary Workaround Pending Upstream Fix**
- Upstream library has bug
- Immediate workaround needed
- Permanent fix pending upstream release
- Example: Third-party API timeout

### ❌ When NOT to Bypass

**Never bypass for:**

- ❌ **Lazy commits** — "I don't want to fix the style issues"
- ❌ **Avoiding code review** — "I'll commit without review"
- ❌ **Skipping tests** — "Tests are inconvenient"
- ❌ **Committing secrets** — "It's faster than using env vars"
- ❌ **Violating SPEC** — "I'll add external scripts just this once"
- ❌ **Bypassing quality gates** — "I trust my code"
- ❌ **Avoiding documentation** — "I'll document later"
- ❌ **Routine work** — "This is just a small fix"

**If you're tempted to bypass, ask yourself:**
- Is this a genuine emergency? (production down, security threat)
- Is there a real time constraint? (not just convenience)
- Have I tried fixing the root cause instead?
- Would a Lead Engineer approve this bypass?

---

## Bypass Methods

### Method 1: BYPASS_HOOK_VALIDATION (Pre-Commit Only)

**What it does:**
- Skips SPEC.md compliance checks
- Skips secret detection
- Skips YAML/JSON validity
- Skips code style checks
- **DOES NOT skip:** commit-msg hook (message format still validated)

**When to use:**
- Committing temporary workaround that violates SPEC
- Temporary external script for production fix
- Temporary cron job for data sync
- Temporary configuration that doesn't meet standards

**Syntax:**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "message"
```

**Example 1: Temporary cron job**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: temporary cron job for production data sync

SKIP_HOOKS: temporary workaround for data sync
reason: production data sync failing, immediate fix required
approved_by: lead-engineer-name

This is a temporary cron job to fix production data sync.
Will be replaced with agent-based solution in follow-up task.

Task: 2026-05-16-production-data-sync-workaround"
```

**Example 2: Temporary external script**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: temporary deployment script

SKIP_HOOKS: temporary script for emergency deployment
reason: CI/CD pipeline broken, immediate deployment needed
approved_by: devops-engineer-name

This is a temporary script to deploy hotfix.
Will be replaced with proper CI/CD in follow-up task.

Task: 2026-05-16-cicd-pipeline-fix"
```

**Post-bypass checklist:**
- [ ] Reason documented in commit message
- [ ] Lead Engineer approval documented
- [ ] Follow-up task created (YYYY-MM-DD-task-name)
- [ ] No real secrets committed
- [ ] Hooks re-enabled: `git config core.hooksPath .githooks`
- [ ] Root cause fix planned

---

### Method 2: SKIP_COMMIT_MSG_HOOK (Commit-Msg Only)

**What it does:**
- Skips message length validation
- Skips conventional commit format check
- Skips DELEGATE/HANDBACK validation
- Skips SKIP_HOOKS documentation requirement

**When to use:**
- Emergency commit with minimal message
- Hotfix that needs immediate deployment
- Temporary fix with minimal documentation

**Syntax:**
```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "message"
```

**Example:**
```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "hotfix: database connection pool"
```

**Note:** This method is rarely needed. Usually, you can write a proper commit message even in emergencies.

**Post-bypass checklist:**
- [ ] Reason documented (if possible)
- [ ] Follow-up commit with full documentation planned
- [ ] Hooks re-enabled: `git config core.hooksPath .githooks`

---

### Method 3: SKIP_HOOKS (Pre-Push Only)

**What it does:**
- Skips agent YAML validation
- Skips workflow file validation
- Skips documentation consistency checks
- Skips DELEGATE/HANDBACK protocol validation
- Skips test suite execution
- Skips SPEC compliance verification

**When to use:**
- Pushing code that failed pre-push validation
- Pushing code that has test failures (but you've verified it's safe)
- Pushing code with documentation issues (but you've verified it's correct)

**Syntax:**
```bash
SKIP_HOOKS=1 git push
```

**Example 1: Push with test failures (verified safe)**
```bash
# 1. Verify tests locally
pytest tests/ -v

# 2. Identify which tests are failing and why
# (e.g., test environment issue, not code issue)

# 3. Push with bypass
SKIP_HOOKS=1 git push origin hotfix-branch

# 4. Create follow-up task to fix tests
```

**Example 2: Push with documentation issues (verified correct)**
```bash
# 1. Verify documentation is correct (even if hook says it's wrong)
cat docs/SPEC.md | head -20

# 2. Push with bypass
SKIP_HOOKS=1 git push origin feature-branch

# 3. Create follow-up task to update hook validation
```

**Post-bypass checklist:**
- [ ] Reason documented in commit message
- [ ] Code verified to be safe (even if hook says it's not)
- [ ] Tests reviewed (if skipped)
- [ ] Documentation verified (if skipped)
- [ ] Follow-up task created to fix root cause
- [ ] Hooks re-enabled: `git config core.hooksPath .githooks`

---

### Method 4: --no-verify (ALL HOOKS - STRONGLY DISCOURAGED)

**What it does:**
- Skips ALL hooks (pre-commit, commit-msg, pre-push)
- Completely bypasses SDLC enforcement

**⚠️ WARNING:** This is the nuclear option. Use ONLY if:
- All other bypass methods have failed
- You have explicit authorization from Lead Engineer or above
- It's a genuine emergency

**Syntax:**
```bash
git commit --no-verify -m "message"
git push --no-verify
```

**Why it's discouraged:**
- Breaks audit trail
- Violates SPEC.md completely
- Prevents quality gate validation
- Can introduce secrets into repo
- Difficult to track and audit

**If you must use this method:**

```bash
# 1. Document extensively in commit message
git commit --no-verify -m "EMERGENCY BYPASS: production outage fix

⚠️  WARNING: This commit bypasses ALL hooks (--no-verify)
    Only use in genuine emergencies with Lead Engineer approval.

EMERGENCY DETAILS:
- Reason: Production database down, all requests failing
- Approved by: lead-engineer-name
- Ticket: PROD-12345
- Duration: Emergency only (max 1 hour)

BYPASS JUSTIFICATION:
- All other bypass methods attempted and failed
- Immediate fix required to restore service
- Cannot wait for hook fixes

CHANGES:
- Increased database connection pool size
- Added connection timeout
- Added monitoring alerts

POST-BYPASS RECOVERY:
- Follow-up task: 2026-05-16-database-pool-permanent-fix
- Root cause analysis required
- Proper solution to be implemented in follow-up
- Hooks will be re-enabled immediately after push"

# 2. Push with --no-verify
git push --no-verify

# 3. Immediately create follow-up task
# 4. Immediately re-enable hooks
git config core.hooksPath .githooks

# 5. Fix root cause in follow-up commit (with hooks enabled)
```

**Post-bypass checklist:**
- [ ] Extensive documentation in commit message
- [ ] Lead Engineer approval documented
- [ ] Ticket reference included
- [ ] Root cause analysis planned
- [ ] Follow-up task created
- [ ] Hooks re-enabled immediately
- [ ] Root cause fix committed in follow-up (with hooks enabled)

---

## Required Documentation for Bypass

### Documentation Template

Every bypass **MUST** be documented with:

1. **What was bypassed** (which hook, what checks)
2. **Why it was necessary** (genuine emergency reason)
3. **Who approved it** (Lead Engineer or above)
4. **How long it's valid** (temporary, max duration)
5. **What comes next** (follow-up task to fix root cause)

### Example: Complete Bypass Documentation

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: production database connection pool fix

═══════════════════════════════════════════════════════════════
EMERGENCY BYPASS DOCUMENTATION
═══════════════════════════════════════════════════════════════

BYPASS METHOD: BYPASS_HOOK_VALIDATION=true
SKIPPED CHECKS: SPEC compliance, secret detection, YAML validity

EMERGENCY REASON:
- Production database connection pool exhausted
- All requests failing with 'too many connections' error
- Service down for 15+ minutes
- Immediate fix required to restore functionality

AUTHORIZATION:
- Approved by: lead-engineer-name
- Approval timestamp: 2026-05-16 14:30 UTC
- Ticket: PROD-12345

BYPASS VALIDITY:
- Duration: Emergency only (max 2 hours)
- Expiration: 2026-05-16 16:30 UTC
- If not fixed by then, escalate to Principal Engineer

CHANGES MADE:
- Increased connection pool size from 10 to 50
- Added connection timeout of 30 seconds
- Added logging for connection pool status
- Restarted database service

TESTING:
- Verified service recovery
- Monitored error logs for 30 minutes
- No new errors observed
- Load testing shows stable performance

POST-BYPASS RECOVERY:
- Follow-up task: 2026-05-16-database-pool-permanent-fix
- Root cause analysis: Connection pool configuration too small
- Permanent solution: Implement dynamic pool sizing
- Timeline: Fix in next sprint

HOOKS STATUS:
- Pre-commit hook: BYPASSED (SPEC checks skipped)
- Commit-msg hook: ACTIVE (message format still validated)
- Pre-push hook: ACTIVE (quality gates still enforced)
- Re-enabled after push: YES

AUDIT TRAIL:
- Commit hash: abc123def456
- Committed by: engineer-name
- Timestamp: 2026-05-16 14:35 UTC
- Pushed to: main (protected branch)

═══════════════════════════════════════════════════════════════"
```

### Minimal Documentation (Acceptable)

If you're in a real emergency and can't write extensive documentation:

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: production fix

Reason: Database down, immediate fix required
Approved: lead-engineer-name
Task: 2026-05-16-database-pool-fix"
```

**But follow up with:**
```bash
# Create detailed documentation in follow-up commit
git commit -m "docs: document emergency bypass from 2026-05-16

Detailed analysis of production outage and emergency fix.
See commit abc123def456 for bypass details."
```

---

## Authorization Requirements

### Who Can Authorize Bypass?

**Can authorize bypass:**
- ✅ Lead Engineer or above
- ✅ On-call engineer (for production emergencies)
- ✅ Security Engineer (for security vulnerabilities)
- ✅ Principal Engineer (for any reason)

**Cannot authorize bypass:**
- ❌ Individual contributors (without Lead Engineer approval)
- ❌ Orchestrator or other agents (must escalate to human)
- ❌ Automated systems (CI/CD, cron jobs, etc.)

### How to Get Authorization

**For production emergencies:**
1. Contact on-call engineer or Lead Engineer
2. Explain the emergency (what's down, impact, timeline)
3. Get verbal approval (document in commit message)
4. Use bypass with documentation
5. Create follow-up task

**For security vulnerabilities:**
1. Contact Security Engineer
2. Explain the vulnerability (CVE, impact, timeline)
3. Get written approval (document in commit message)
4. Use bypass with documentation
5. Create follow-up task

**For other emergencies:**
1. Contact Lead Engineer
2. Explain the emergency (what's broken, impact, timeline)
3. Get approval (document in commit message)
4. Use bypass with documentation
5. Create follow-up task

---

## Post-Bypass Recovery

### Immediate Actions (Within 1 Hour)

1. **Verify the fix worked:**
   ```bash
   # Check that service is restored
   # Check that no new errors appeared
   # Check that monitoring is stable
   ```

2. **Re-enable hooks:**
   ```bash
   git config core.hooksPath .githooks
   git config core.hooksPath  # verify it's set
   ```

3. **Create follow-up task:**
   ```bash
   # Add to TODO.md or create GitHub issue
   - [ ] Fix root cause of bypass: {description}
   - [ ] Task: 2026-05-16-{task-name}
   - [ ] Approved by: {approver-name}
   - [ ] Deadline: {when to fix by}
   ```

4. **Notify team:**
   ```bash
   # Post in Slack/email
   "Emergency bypass used at 2026-05-16 14:35 UTC for {reason}.
    Service restored. Follow-up task created: 2026-05-16-{task-name}"
   ```

### Short-Term Actions (Within 24 Hours)

1. **Root cause analysis:**
   - Why did this happen?
   - Could it have been prevented?
   - What's the permanent fix?

2. **Create detailed follow-up commit:**
   ```bash
   git commit -m "fix: address root cause of emergency bypass

   - Root cause: Connection pool configuration too small
   - Permanent solution: Implement dynamic pool sizing
   - Testing: Load tested with 1000 concurrent connections
   - Monitoring: Added alerts for connection pool usage
   - Ticket: PROD-12345"
   ```

3. **Update documentation:**
   - Document what happened
   - Document what was fixed
   - Document how to prevent in future

### Long-Term Actions (Within 1 Sprint)

1. **Implement permanent fix:**
   - Not just a workaround
   - Proper solution that passes all hooks
   - Full test coverage

2. **Update monitoring/alerting:**
   - Alert before problem occurs again
   - Automated recovery if possible
   - Runbook for on-call engineer

3. **Post-mortem (if serious):**
   - What happened?
   - Why did it happen?
   - What did we learn?
   - How do we prevent in future?

---

## Audit Trail

### How Bypasses Are Tracked

**Commit message:**
```bash
git log --all --grep="SKIP_HOOKS\|BYPASS\|emergency" --oneline
```

**Bypass markers in code:**
```bash
git log -p | grep -i "skip_hooks\|bypass_hook"
```

**Environment variables used:**
```bash
# Check git history for bypass commands
history | grep -E "SKIP_HOOKS|BYPASS_HOOK"
```

### Audit Trail Requirements

Every bypass must have:
- [ ] Documented reason in commit message
- [ ] Approver name documented
- [ ] Ticket/issue reference (if applicable)
- [ ] Timestamp of bypass
- [ ] Follow-up task created
- [ ] Hooks re-enabled after push

### Example Audit Trail

```bash
# 1. Check for bypasses
git log --all --oneline | grep -i "emergency\|bypass"
# Output: abc123d emergency: production database fix

# 2. View full commit details
git show abc123d
# Output: Shows complete documentation of bypass

# 3. Check follow-up task
git log --all --oneline | grep "2026-05-16-database-pool-fix"
# Output: Shows follow-up task was created

# 4. Verify hooks were re-enabled
git config core.hooksPath
# Output: .githooks (verified)
```

---

## Bypass Checklist

### Pre-Bypass Checklist

Before using bypass, verify:
- [ ] This is a genuine emergency (production down, security threat, etc.)
- [ ] There's a real time constraint (not just convenience)
- [ ] I've tried fixing the root cause instead
- [ ] I have authorization from Lead Engineer or above
- [ ] I've documented the reason in the commit message
- [ ] I've created a follow-up task to fix root cause
- [ ] I understand the risks of bypassing quality gates

### During-Bypass Checklist

While using bypass:
- [ ] Using correct bypass method for the situation
- [ ] Documenting reason in commit message
- [ ] Including approver name
- [ ] Including ticket/issue reference
- [ ] Including follow-up task ID
- [ ] Committing/pushing successfully
- [ ] Verifying the fix worked

### Post-Bypass Checklist

After using bypass:
- [ ] Verified the fix worked (service restored, no new errors)
- [ ] Re-enabled hooks: `git config core.hooksPath .githooks`
- [ ] Created follow-up task to fix root cause
- [ ] Notified team of bypass and follow-up task
- [ ] Started root cause analysis
- [ ] Scheduled permanent fix
- [ ] Updated monitoring/alerting if needed
- [ ] Closed follow-up task when permanent fix is complete

---

## Common Bypass Scenarios

### Scenario 1: Production Database Down

**Emergency:** Database connection pool exhausted, all requests failing

**Bypass method:** `BYPASS_HOOK_VALIDATION=true`

**Why:** Need to commit temporary workaround (increase pool size) quickly

**Steps:**
```bash
# 1. Make emergency fix
# Edit config to increase connection pool size

# 2. Commit with bypass
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: increase database connection pool

Reason: Connection pool exhausted, service down
Approved: on-call-engineer-name
Task: 2026-05-16-database-pool-permanent-fix"

# 3. Push (hooks still validate)
git push origin main

# 4. Verify service restored
# Check monitoring, error logs, etc.

# 5. Create follow-up task
# Plan permanent fix for next sprint
```

### Scenario 2: Critical Security Vulnerability

**Emergency:** SQL injection vulnerability discovered in production

**Bypass method:** `BYPASS_HOOK_VALIDATION=true` (if needed)

**Why:** May need to commit temporary workaround quickly

**Steps:**
```bash
# 1. Make emergency fix
# Add input validation to vulnerable endpoint

# 2. Commit with bypass (if needed)
BYPASS_HOOK_VALIDATION=true git commit -m "security: fix SQL injection vulnerability

Vulnerability: SQL injection in user search endpoint
CVE: CVE-2026-12345
Approved: security-engineer-name
Task: 2026-05-16-sql-injection-permanent-fix"

# 3. Push (hooks still validate)
git push origin main

# 4. Verify vulnerability is fixed
# Run security tests, penetration testing, etc.

# 5. Create follow-up task
# Plan permanent fix and security audit
```

### Scenario 3: CI/CD Pipeline Broken

**Emergency:** Build pipeline broken, team cannot merge code

**Bypass method:** `SKIP_HOOKS=1 git push` (if needed)

**Why:** May need to push hotfix to fix CI/CD

**Steps:**
```bash
# 1. Identify CI/CD issue
# Check GitHub Actions logs, build configuration, etc.

# 2. Make fix to CI/CD configuration
# Fix broken workflow, update dependencies, etc.

# 3. Push with bypass (if needed)
SKIP_HOOKS=1 git push origin main

# 4. Verify CI/CD is working
# Check that builds pass, tests run, etc.

# 5. Create follow-up task
# Plan permanent CI/CD improvements
```

### Scenario 4: Test Environment Misconfiguration

**Emergency:** Tests failing due to environment issue, not code issue

**Bypass method:** `SKIP_HOOKS=1 git push`

**Why:** Tests are failing, but code is correct

**Steps:**
```bash
# 1. Verify code is correct
# Review changes, run tests locally, etc.

# 2. Identify test environment issue
# Check test configuration, database setup, etc.

# 3. Push with bypass
SKIP_HOOKS=1 git push origin feature-branch

# 4. Fix test environment
# Update test configuration, reset database, etc.

# 5. Verify tests pass
# Run tests again to confirm

# 6. Create follow-up task
# Plan test environment improvements
```

---

## FAQ

**Q: Can I bypass hooks without documentation?**  
A: No. Every bypass must be documented with reason, approver, and follow-up task. Undocumented bypasses are security violations.

**Q: Who can authorize a bypass?**  
A: Lead Engineer or above. Individuals cannot authorize their own bypasses.

**Q: What if I bypass without authorization?**  
A: This is a serious violation. The commit may be reverted, and disciplinary action may be taken.

**Q: How long can I use a bypass?**  
A: Bypasses are for emergencies only. Temporary workarounds should be fixed within 24 hours. Permanent bypasses are not allowed.

**Q: Can I use bypass for routine work?**  
A: No. Bypass is for genuine emergencies only. Routine work must pass all hooks.

**Q: What if I need to bypass multiple times?**  
A: This indicates a systemic problem. Contact Lead Engineer to discuss root cause and permanent solution.

**Q: Can automated systems use bypass?**  
A: No. All automated systems must pass hooks. If a system needs to bypass, it's a sign the hooks are too strict.

**Q: What if a hook is broken?**  
A: Report it immediately with reproduction steps. Use bypass with documentation while it's being fixed.

---

## Update Log

- **2026-05-16:** Initial comprehensive bypass procedures documentation with authorization requirements, audit trail, and recovery procedures.
