---
name: Quality Engineer + Self-Healing Framework Design
description: Architecture for comprehensive quality verification with self-healing feedback loop
type: design
version: 1.0
date: 2026-04-27
---

# Quality Engineer + Self-Healing Framework — Architecture Design (Phase 5.1)

## Overview

Design for comprehensive Quality Engineer role with self-healing feedback loop. Enables:
1. **Comprehensive pre-deployment verification** (testing, security, compliance, requirements)
2. **Intelligent issue diagnosis** (root cause analysis with confidence scoring)
3. **Automated healing** of low-risk, pattern-matchable issues (Healer Engineer)
4. **Escalation to humans** for high-risk decisions
5. **Re-validation** after healing (quality gates run again)

---

## 5 Key Architectural Decisions

### Decision 1: Testing Pyramid 2.0 (Adapted for Agents)

**What**: Multi-layer testing strategy adapted for AI agent non-determinism

**Base Layer** (Deterministic Components):
- Unit tests: Fast, deterministic, <80% coverage
- Integration tests: Medium cost, service interactions (EventBridge, DynamoDB, SNS)
- Test execution: Parallel where safe

**Middle Layer** (Agent-Specific):
- Tool call verification (not exact output verification)
- Agent flow validation (right sequence of tool calls)
- Ragas-style ground-truth validation

**Top Layer** (User Workflows):
- E2E tests (Playwright): Full user scenarios
- Expensive: only run pre-deployment, not per-commit
- Coverage: login → action → side effects → projection update

**Why**: Avoids expensive E2E on every commit; strategic pre-deployment verification

**Implementation**:
- `test-unit-orchestration.md` — unit discovery + coverage
- `test-integration-orchestration.md` — mock ERS services
- `test-e2e-orchestration.md` — Playwright scenario filtering
- `test-business-logic.md` — parametric testing, edge cases, state machines

---

### Decision 2: Semantic Security Scanning (Data Flow Analysis)

**What**: Claude-based security scanning that understands component interaction, not just pattern matching

**Approach** (from Anthropic):
- Read code like human security researcher
- Trace data flows across files
- Identify complex multi-component vulnerabilities
- Adversarial verification: challenge findings before surfacing

**Why**: Catches CQRS/event-driven vulnerabilities that pattern matching misses
- Example: Event published but consumer doesn't validate sender (privilege escalation)
- Example: JWT scope checked in gateway but not enforced in Lambda (bypass)

**Tools Integration**:
- `security-semantic-scan.md` — Claude-based data flow analysis
- `security-dependency-scan.md` — go vuln, npm audit, cargo audit (tool orchestration)
- `security-secret-detection.md` — truffleHog, pattern matching for hardcoded creds

**Confidence & Escalation**:
- Semantic findings: always escalate to Security Engineer (high false positive risk)
- Dependency findings: auto-fix vulnerabilities if confidence >90% (e.g., version bump)
- Secret findings: critical, block deployment immediately

---

### Decision 3: Requirement Traceability (REQ → Test → Code → Deployment)

**What**: Explicit mapping ensuring feature completeness and test coverage

**Mapping Structure**:
```
REQ-001-user-role-admin
  ├─ Specification: "Admin users can approve/reject events"
  ├─ Tests:
  │   ├─ test_user_role_transition_to_admin()
  │   ├─ test_admin_can_approve_event()
  │   └─ test_admin_can_reject_event()
  ├─ Code:
  │   ├─ handlers.go:AdminApprovalHandler()
  │   └─ models.go:User.IsAdmin()
  └─ Coverage: 3/3 tests passing → 100% coverage
```

**Pre-Deployment Gate**: All requirements must have ≥1 test AND all tests passing

**Why**: Prevents orphaned code, ensures feature completeness, audit trail for compliance

**Implementation**:
- `requirement-mapping.md` — parse specs, link to tests, report coverage
- `requirement-verification.md` — gate: all requirements tested?

---

### Decision 4: Self-Healing Feedback Loop (Detect → Diagnose → Route → Act → Re-validate)

**What**: Automatic fixing of low-risk issues, escalation of high-risk

**Three Maturity Levels**:

**Level 1: Passive Observation**
- Detect failures, log
- Humans review all failures

**Level 2: Intelligent Routing** (START HERE)
- Detect → diagnose → route to human
- Safe, low automation risk
- Good for earning trust

**Level 3: Healers** (AFTER TRUST)
- Detect → diagnose → auto-fix (if safe) → re-validate → proceed
- Humans only review escalations
- High efficiency, requires guardrails

**Root Cause Categories**:
- **Dependency**: Missing version, conflict, outdated
- **Configuration**: Missing env var, wrong path, permissions
- **Test Flakiness**: Timing issue, data setup problem, concurrency race
- **Logic Regression**: Code bug (requires code review)
- **Infrastructure**: Service unavailable, network issue

**Routing Decision**:
```
Issue detected
  ↓
Diagnostic engine analyzes
  ├─ Root cause identified
  ├─ Confidence score: HIGH or LOW
  └─ Risk assessment: LOW or HIGH
      ↓
HIGH confidence + LOW risk (pattern-matchable)
  → Route to Healer Engineer (auto-fix)
      ↓
LOW confidence OR HIGH risk
  → Escalate to Lead/Principal/Security (human decision)
```

**Healer Constraints** (LOW RISK ONLY):
- ✅ Missing env var → add to .env
- ✅ Dependency version → update go.mod/package.json
- ✅ Flaky test → add retry + stabilize setup
- ✅ Lockfile stale → regenerate
- ✅ Import wrong → fix path
- ❌ Logic bug → code review needed
- ❌ Security issue → Security review needed
- ❌ Architecture change → design decision needed

**Auto-Merge Guardrails**:
- All quality gates pass (tests, security, compliance)
- No human escalations triggered
- Single, isolated change (not multi-file refactoring)
- Audit trail complete (who, what, when, outcome)

**Implementation**:
- `issue-diagnostic-engine.md` — root cause analysis + confidence scoring
- `healer-engineer.md` — auto-fix low-risk issues + create PR
- `quality-gate-orchestration.md` — master orchestrator + self-healing loop

---

### Decision 5: Escalation Thresholds & Role Responsibilities

**What**: Clear boundaries for when to escalate, which role handles which issue type

**Escalation Paths**:

```
Engineer (base level execution)
  ├─ Runs quality gates
  ├─ Reports issues to Orchestrator
  └─ Awaits Healer/escalation result

Healer Engineer (new role — auto-fixes)
  ├─ Triggered by Orchestrator (HIGH confidence + LOW risk issues)
  ├─ Auto-fixes: missing vars, dependency versions, flaky tests
  ├─ Creates PR + optional auto-merge
  └─ Escalates if fix PR fails CI

Lead Engineer (unblocking authority)
  ├─ Reviews Healer escalations
  ├─ Reviews LOW confidence or MEDIUM risk issues
  ├─ Makes architectural decisions (if needed)
  └─ Approves fix approach + Engineer implements

Principal Engineer (architecture decisions)
  ├─ Reviews HIGH risk or strategic issues
  ├─ Approves major changes
  └─ Validates security/architectural implications

Security Engineer (security decisions)
  ├─ Reviews all security findings (HIGH priority)
  ├─ Assesses real vs false positive
  ├─ Approves security patches
  └─ Escalates critical issues immediately

Orchestrator (coordinator)
  ├─ Monitors quality gates
  ├─ Routes issues to Healer/escalation
  ├─ Tracks healing outcomes
  └─ Integrates results + proceeds/blocks deployment
```

**Token Budget Awareness**:
- Per-commit: unit tests (~30s, Haiku)
- Per-push: E2E tests (~2-5 min, Sonnet)
- Pre-deploy: comprehensive verification + security (~10-15 min, Opus for security)
- Healer fixes: low cost if pattern-matchable (Sonnet)
- Escalations: higher cost (Principal/Security = Opus)

---

## Implementation Phases

### 5.1: Architecture + Design (THIS DOCUMENT) ✅
- 5 key decisions documented
- Roles and escalation paths defined
- Token budget awareness

### 5.2-5.7: Parallel Skill Building (6 days)
See TODO.md Phase 5 for detailed skill specifications and delegation

### 5.8: Integration + Documentation
- All 12 skills working end-to-end
- Self-healing loop validated
- Role definitions complete

---

## Success Criteria

- [x] 5 key architectural decisions documented with rationale
- [ ] 12 skills implemented (see TODO.md for checklist)
- [ ] Testing pyramid working (unit/integration/E2E)
- [ ] Semantic security scanning finding real vulnerabilities
- [ ] Requirement traceability mapped for 1 service
- [ ] Self-healing loop tested end-to-end (detect → diagnose → heal → validate)
- [ ] Healer Engineer successfully auto-fixes low-risk issues
- [ ] Escalation path functional (high-risk issues → human review)
- [ ] Audit trail tracks all Healer actions

---

## Related Documents

- `TODO.md` → Phase 5 full breakdown (5.1-5.8)
- `PHASE-5-UPDATED-SUMMARY.md` → Overview + timeline
- `QUALITY-ENGINEER-RESEARCH.md` → Research findings
- `PHASE-5-ORCHESTRATOR-BRIEF.md` → Delegation strategy

---

**Version**: 1.0  
**Status**: Design complete, ready for implementation delegation  
**Next**: Phase 5.2-5.7 parallel skill building
