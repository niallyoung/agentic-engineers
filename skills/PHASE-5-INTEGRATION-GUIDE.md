---
name: Phase 5.8+ Production Integration Guide
description: Integrating quality-gate-orchestration into GitHub Actions, Makefile, and pre-push hooks
type: integration-guide
date: 2026-04-28
---

# Phase 5.8+ Production Integration Guide

## Overview

This guide documents how to integrate the 13 Phase 5 quality skills (including master orchestrator and Healer Engineer) into the existing ERS SDLC workflow.

**Integration points:**
1. Local pre-push hook (lightweight, skip E2E)
2. Makefile target (full quality check)
3. GitHub Actions main.yaml (pre-deployment gate for prod)
4. Orchestrator role (task routing, metrics)

---

## Architecture

```
Developer Workflow
  │
  ├─ Edit code + commit
  │   └─ pre-commit hook: lint + test (existing)
  │
  ├─ git push
  │   └─ pre-push hook: verify quality locally
  │       ├─ Run: make quality-gate (skip E2E for speed)
  │       ├─ If issues found: diagnose + suggest auto-fixes
  │       ├─ Allow override: git push --no-verify
  │       └─ Proceed to GitHub Actions
  │
  └─ Cloud CI (main.yaml)
      ├─ Job: build-deploy-dev (existing)
      ├─ Job: quality-gate-prod (NEW)
      │   └─ Run: make quality-gate --deployment-target prod
      │   ├─ Phase 1: Parallel quality checks (tests + security + compliance)
      │   ├─ Phase 2: Initial gate decision
      │   ├─ Phase 3: Self-healing (route issues → Healer → re-validate)
      │   ├─ Phase 4: Final decision (PROCEED | WARN | BLOCK | ESCALATE)
      │   └─ Output: gate_decision + audit_trail JSON
      │
      └─ Job: deploy-prod (only if quality-gate PROCEED)
```

---

## Phase 5.8a: Add Makefile Target

Update all ERS service Makefiles to include `quality-gate` target:

```makefile
quality-gate: describe
	@printf "$(MAGENTA)################ make quality-gate$(RESET)\n"
	/quality-gate-orchestration . \
		--deployment-target=$(ENV_NAME) \
		--validate-migrations \
		--skip-e2e \
		--json
.PHONY: quality-gate

quality-gate-full: describe
	@printf "$(MAGENTA)################ make quality-gate-full$(RESET)\n"
	/quality-gate-orchestration . \
		--deployment-target=$(ENV_NAME) \
		--validate-migrations \
		--json
.PHONY: quality-gate-full
```

**Targets:**
- `make quality-gate` — quick check (skip E2E), used in pre-push hook
- `make quality-gate-full` — full check (E2E included), used in CI before prod deployment

---

## Phase 5.8b: Update GitHub Actions main.yaml

Add new job between `build-deploy-dev` and `deploy-prod`:

```yaml
quality-gate-prod:
  name: Quality Gate — Pre-Deployment
  if: github.ref == 'refs/heads/main'
  needs: build-deploy-dev
  runs-on: ubuntu-latest
  container:
    image: ghcr.io/{your-org}/ci-image:latest
    credentials:
      username: ${{ github.actor }}
      password: ${{ secrets.GHCR_TOKEN }}
  concurrency:
    group: {example-service}-quality
    cancel-in-progress: false
  steps:
    - uses: actions/checkout@v4

    - name: Configure git
      run: git config --global --add safe.directory "$GITHUB_WORKSPACE"

    - name: Run Quality Gates
      id: quality
      run: ENV_NAME=prod make quality-gate-full
      continue-on-error: true

    - name: Quality Gate Decision
      run: |
        RESULT="${{ steps.quality.outcome }}"
        if [ "$RESULT" == "success" ]; then
          echo "✅ Quality gates PASSED"
          exit 0
        else
          echo "⚠️  Quality gates FAILED — review diagnostics above"
          exit 1
        fi

deploy-prod:
  name: Deploy Prod & Tag
  if: github.ref == 'refs/heads/main'
  needs: [build-deploy-dev, quality-gate-prod]  # ADD quality-gate-prod HERE
  ...
```

---

## Phase 5.8c: Update Pre-Push Hook

Add quality gate check to pre-push hook in `{workspace-name}/githooks/pre-push`:

```bash
# Quality gate check (skip E2E for speed)
if command -v /quality-gate-orchestration >/dev/null 2>&1; then
  echo "🔍 Running local quality gates..."
  ENV_NAME=dev make quality-gate --skip-e2e
  if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Quality gates failed. Review diagnostics above."
    echo "   To skip this check: git push --no-verify"
    echo ""
    exit 1
  fi
else
  echo "⚠️  quality-gate-orchestration not available, skipping local quality check"
fi
```

---

## Phase 5.8d: Test on {example-service} (Baseline Service)

### Step 1: Verify quality-gate-orchestration is available

```bash
which /quality-gate-orchestration
# or
/quality-gate-orchestration --help
```

### Step 2: Dry-run locally

```bash
cd $WORKSPACE_ROOT/{example-service}

# Quick check (dev, skip E2E)
ENV_NAME=dev make quality-gate

# Full check (with E2E)
ENV_NAME=dev make quality-gate-full

# Prod check (strictest requirements)
ENV_NAME=prod make quality-gate-full
```

### Step 3: Review output

Quality gate returns structured JSON:
```json
{
  "timestamp": "2026-04-28T12:00:00Z",
  "service": "{example-service}",
  "deployment_target": "prod",
  "phase_1": {
    "status": "PASS",
    "tests": { "unit": "PASS", "integration": "PASS", "e2e": "PASS" },
    "security": { "semantic": "PASS", "dependencies": "PASS", "secrets": "PASS" },
    "compliance": { "requirements": "PASS", "specs": "PASS" }
  },
  "phase_2": {
    "initial_gate_decision": "PROCEED"
  },
  "phase_3": {
    "healing_attempts": 0,
    "healer_prs_created": 0
  },
  "phase_4": {
    "final_decision": "PROCEED",
    "audit_trail": [...]
  }
}
```

### Step 4: Test self-healing workflow

Intentionally introduce a low-risk issue to trigger Healer:

```bash
# Example: Add a missing environment variable to test
# (Healer should detect + auto-fix)

# Run quality gates
ENV_NAME=dev make quality-gate-full

# Check for Healer PR:
gh pr list --repo {your-org}/{example-service} --state open
```

---

## Phase 5.8e: Validation Checklist

### Local Testing
- [ ] `make quality-gate` runs in <2 min (skip E2E)
- [ ] `make quality-gate-full` runs in <10 min (with E2E)
- [ ] Output is valid JSON
- [ ] gate_decision is PROCEED, WARN, BLOCK, or ESCALATE
- [ ] Healer auto-fixes low-risk issues correctly
- [ ] Escalation paths work (high-risk → human review)

### GitHub Actions Testing
- [ ] Update main.yaml with quality-gate-prod job
- [ ] Create test branch (e.g., test/phase-5-integration)
- [ ] Push to test branch to trigger cloud CI
- [ ] Verify quality-gate-prod job runs before deploy-prod
- [ ] Confirm deploy-prod only runs if quality-gate-prod passes

### End-to-End Testing
- [ ] Introduce intentional bug
- [ ] Push to main
- [ ] Verify quality gates catch bug
- [ ] Verify Healer auto-fixes (if eligible)
- [ ] Verify escalation (if not eligible)

---

## Phase 5.9: Rollout to All 8 ERS Services

Once Phase 5.8 validation is complete on {example-service}:

### Services to Update (in order)
1. ✅ **{example-service}** (baseline, Phase 5.8)
2. **{example-service}** (read gateway, similar to {example-service})
3. **{service-name}** (event consumer, DynamoDB)
4. **{example-service}** (EventStore, critical path)
5. **{service-name}** (event consumer, SES)
6. **{example-service}** (Cognito integration, sensitive)
7. **{service-name}** (file sync, Lambda)
8. **{service-name}** (deprecated, lower priority)

### For Each Service
1. Add `quality-gate` + `quality-gate-full` targets to Makefile
2. Update `.github/workflows/main.yaml` (add quality-gate-prod job)
3. Update pre-push hook (if not using global hook)
4. Local validation: `ENV_NAME=prod make quality-gate-full`
5. Push to test branch, verify GitHub Actions
6. Update service-specific documentation

---

## Phase 5.10: Monitoring & Continuous Improvement

### Metrics to Track
- **Healer Success Rate**: % of issues auto-fixed without human intervention
  - Target: >70%
- **Mean Time to Fix**: Healer time vs human review time
  - Expected: <5 min (Healer) vs hours (human)
- **False Negative Rate**: Issues marked "LOW risk" that broke something
  - Target: <5%
- **Quality Gate Execution Time**: Duration of full quality check
  - Target: <10 min per service

### Feedback Loop
1. Healer auto-fixes → CI passes/fails
2. Collect outcome (success/failure) → issue-diagnostic-engine
3. Adjust confidence scoring based on real outcomes
4. Gradually graduate from Level 2 (routing) to Level 3 (full Healer autonomy)

### Audit Trail Analysis
- Review `healer-audit-log.jsonl` weekly
- Identify patterns in auto-fixed issues
- Update Healer constraints based on outcomes
- Adjust diagnostic engine confidence scores

---

## Integration Checklist

### Pre-Implementation
- [ ] All 13 Phase 5 skills built and committed
- [ ] quality-gate-orchestration.md documented
- [ ] healer-engineer.md role defined
- [ ] issue-diagnostic-engine.md with confidence scoring

### Implementation
- [ ] Phase 5.8a: Add Makefile targets to all services
- [ ] Phase 5.8b: Update GitHub Actions main.yaml
- [ ] Phase 5.8c: Update pre-push hooks
- [ ] Phase 5.8d: Local validation on {example-service}
- [ ] Phase 5.8e: Self-healing workflow test

### Validation
- [ ] Quality gate local execution <2 min (skip E2E)
- [ ] Quality gate full execution <10 min (with E2E)
- [ ] Healer auto-fixes work correctly
- [ ] Escalation paths functional
- [ ] GitHub Actions integration verified

### Rollout
- [ ] {example-service} baseline complete (Phase 5.8)
- [ ] All 8 services updated (Phase 5.9)
- [ ] Monitoring + metrics collection active (Phase 5.10)
- [ ] Continuous improvement loop established

---

## Troubleshooting

### Issue: quality-gate-orchestration skill not found
**Solution**: Install agentic-engineers skills globally or add to PATH
```bash
# Ensure agentic-engineers is in ~/.agents/agentic-engineers
# Or set up symlinks: ln -s $WORKSPACE_ROOT/agentic-engineers ~/.agents/
```

### Issue: Quality gate times out
**Solution**: Use `--skip-e2e` for quick checks, full E2E only pre-deployment
```bash
make quality-gate              # Skip E2E
make quality-gate-full         # Include E2E (longer)
```

### Issue: Healer PR fails CI after auto-fix
**Solution**: Healer automatically escalates failed PRs to human review
- Check `healer-audit-log.jsonl` for why fix failed
- Adjust diagnostic confidence scoring if repeated pattern
- Or escalate to Lead Engineer for manual review

### Issue: False escalations (low-confidence issues marked HIGH)
**Solution**: Tune issue-diagnostic-engine confidence thresholds
- Review past issues that were escalated but were actually fixable
- Adjust confidence scoring in diagnostic engine
- Re-run quality gates to verify improvement

---

## Success Criteria

✅ **Phase 5.8 Complete When:**
- {example-service} quality gates pass locally
- Self-healing workflow tested end-to-end
- GitHub Actions integration verified
- Audit trail shows expected flow (detect → diagnose → heal/escalate → re-validate)

✅ **Phase 5.9 Complete When:**
- All 8 ERS services have quality gate integration
- Makefile targets work consistently across services
- Pre-push hooks enforce local quality checks

✅ **Phase 5.10 Complete When:**
- Healer success rate tracked and >70%
- Metrics collected for continuous improvement
- Confidence scoring refined based on real outcomes
- Ready to graduate from Level 2 to Level 3 (full autonomy)

---

**Status**: Ready for Phase 5.8 implementation  
**Next**: Begin local testing on {example-service}  
**Target**: Complete Phase 5.8 by 2026-04-29
