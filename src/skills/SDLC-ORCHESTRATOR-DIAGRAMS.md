---
name: SDLC Orchestrator & Quality Flow Diagrams
description: Complete SDLC flow with quality gates, component architecture, sequence diagrams showing agent orchestration
type: reference
---

# SDLC Orchestrator & Quality Flow Diagrams

## Diagram 1: Full SDLC Flow — Credential Detection Example

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEVELOPER WORKFLOW (LOCAL)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Developer edits code, commits                                           │
│     ▼                                                                        │
│  2. Pre-commit hook runs                                                    │
│     ├─ make lint ──────────────────────────┐                               │
│     ├─ make test ──────────────────────────├──→ ✅ All pass                │
│     └─ conventional commits ──────────────┘                                │
│                                                                              │
│  3. Pre-push hook runs                                                      │
│     ├─ E2E tests ────────────────────────┐                                 │
│     ├─ git diff (color review) ─────────┼──→ ✅ E2E pass                  │
│     └─ "Push to main? [y/N]" ──────────┘    Developer says YES             │
│                                                                              │
│  4. git push origin main                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS PIPELINE (CI/CD)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. build-deploy-dev JOB                                                    │
│     ├─ Lint, Test, Build ─────────────────────────┐                        │
│     ├─ Deploy to dev environment ────────────────┼──→ ✅ Dev deployed      │
│     └─ Smoke test dev ───────────────────────────┘                         │
│                                                                              │
│  2. quality-gate-prod JOB (NEW)                                             │
│     │                                                                        │
│     ├─ Phase 1: Parallel Quality Checks                                     │
│     │  ├─ test-unit ──────┐                                                │
│     │  ├─ test-integration│                                                │
│     │  ├─ test-e2e ───────├──→ All checks PASS in ~90s                    │
│     │  ├─ security-deps ──┤                                                │
│     │  ├─ security-secrets├──→ 🚨 DETECTED: HARDCODED_CREDENTIAL          │
│     │  └─ compliance ─────┘                                                │
│     │                                                                        │
│     ├─ Phase 2: Initial Gate Decision                                       │
│     │  └─→ "ISSUES_FOUND" (secret detection = security issue)             │
│     │                                                                        │
│     ├─ Phase 3: Self-Healing Analysis                                       │
│     │  ├─ Issue Diagnostic Engine evaluates:                               │
│     │  │  ├─ Confidence: HIGH (regex pattern match)                        │
│     │  │  ├─ Risk Level: HIGH (production secret)                          │
│     │  │  └─ Auto-fixable: NO (requires human review)                      │
│     │  │                                                                     │
│     │  ├─ Routing Decision:                                                │
│     │  │  ├─ Confidence: HIGH + Risk: HIGH  ─→ ❌ ESCALATE TO HUMAN       │
│     │  │  └─ Send to: Security Engineer (Principal/Opus)                   │
│     │  │                                                                     │
│     │  └─ Create Healer Task (will not proceed auto-fix)                   │
│     │                                                                        │
│     └─ Phase 4: Final Decision                                              │
│        └─→ "ESCALATE" (exit code 1)                                        │
│                                                                              │
│  3. GitHub Actions: Deploy-Prod JOB BLOCKED ❌                              │
│     └─→ Cannot proceed (depends on quality-gate-prod, which failed)         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (PR/Notification sent to developer)
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEVELOPER RESPONSE (LOCAL) — FIX PHASE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Developer sees quality gate failure                                     │
│     ├─ Opens GitHub Actions logs                                           │
│     ├─ Reads: "Security issue detected: hardcoded AWS credential"          │
│     └─ Understands: Line 42 of config.go has exposed secret                │
│                                                                              │
│  2. Developer fixes locally                                                 │
│     ├─ Removes hardcoded credential                                        │
│     ├─ Moves secret to Secrets Manager                                     │
│     ├─ Loads secret from environment at runtime                            │
│     └─ Commits: fix(security): remove hardcoded credential, use env var    │
│                                                                              │
│  3. Pre-commit hook runs again                                              │
│     ├─ make lint ──────────────────────────┐                               │
│     ├─ make test ──────────────────────────├──→ ✅ All pass (no secret)   │
│     └─ conventional commits ──────────────┘                                │
│                                                                              │
│  4. Pre-push hook runs again                                                │
│     ├─ E2E tests ────────────────────────┐                                 │
│     ├─ git diff (color review) ─────────┼──→ ✅ E2E pass                  │
│     └─ "Push to main? [y/N]" ──────────┘    Developer says YES             │
│                                                                              │
│  5. git push origin main (second attempt)                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS PIPELINE — RETRY                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. build-deploy-dev JOB (same as before)                                   │
│     └─→ ✅ Dev deployed successfully                                        │
│                                                                              │
│  2. quality-gate-prod JOB (credential is fixed)                             │
│     │                                                                        │
│     ├─ Phase 1: All checks PASS                                             │
│     │  ├─ test-unit ─────┐                                                 │
│     │  ├─ test-e2e ──────┤                                                 │
│     │  ├─ security-deps ─├──→ ✅ All green (no secret detected)           │
│     │  ├─ security-secrets┤                                                │
│     │  └─ compliance ────┘                                                 │
│     │                                                                        │
│     ├─ Phase 2: Gate Decision → "PROCEED"                                   │
│     ├─ Phase 3: No issues, skip healing                                     │
│     └─ Phase 4: Final Decision → "PROCEED" (exit code 0)                   │
│                                                                              │
│  3. GitHub Actions: Deploy-Prod JOB UNBLOCKED ✅                            │
│     └─→ Can now proceed (quality-gate-prod passed)                          │
│                                                                              │
│  4. deploy-prod JOB                                                         │
│     ├─ Deploy to production ────────────────────────┐                      │
│     ├─ Smoke test prod ─────────────────────────────┼──→ ✅ Prod deployed │
│     └─ Tag release (v1.2.3) ──────────────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION + AUDIT TRAIL                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ✅ Code deployed to production                                             │
│  ✅ Audit trail recorded:                                                   │
│     ├─ Credential detected at time T1                                       │
│     ├─ Escalated to developer at T1+30s                                     │
│     ├─ Developer fixed at T2 (15 min later)                                 │
│     ├─ Re-validation passed at T2+2min                                      │
│     └─ Deployed to prod at T2+10min                                         │
│                                                                              │
│  📊 Metrics recorded for Phase 5.10 improvement:                            │
│     ├─ Issue: credential detection (HIGH confidence)                        │
│     ├─ Resolution time: 15 minutes (developer action)                       │
│     ├─ Quality gate blocked: YES (1 failed push)                            │
│     └─ False positives: 0                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 2: Orchestrator Component Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                      QUALITY GATE ORCHESTRATOR                                │
│                  (quality-gate-orchestration.sh)                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ PHASE 1: PARALLEL QUALITY SKILLS (run in background)                   │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                          │ │
│  │  Skill 1: test-unit                                Skill 5: security-secrets
│  │  ├─ make test                                      ├─ grep credentials
│  │  ├─ Go test runner                                 ├─ Pattern detection
│  │  └─ Result: PASS or FAIL                           └─ Result: PASS, WARN, or FAIL
│  │                                                                          │ │
│  │  Skill 2: test-integration         Skill 4: security-deps               │ │
│  │  ├─ Integration test suite         ├─ Scan go.mod                       │ │
│  │  ├─ Database fixtures             ├─ CVE lookup                        │ │
│  │  └─ Result: PASS or FAIL           └─ Result: PASS or FAIL             │ │
│  │                                                                          │ │
│  │  Skill 3: test-e2e                 Skill 6: compliance-verification     │ │
│  │  ├─ Playwright E2E tests           ├─ Schema validation                 │ │
│  │  ├─ Cross-browser                  ├─ Requirement mapping               │ │
│  │  └─ Result: PASS or FAIL           └─ Result: PASS or FAIL             │ │
│  │                                                                          │ │
│  │                ↓ All results collected                                  │ │
│  │                (wait for all to complete)                              │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ PHASE 2: INITIAL DECISION GATE                                          │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                          │ │
│  │  Evaluate all Phase 1 results:                                          │ │
│  │  ├─ Count: PASS vs FAIL vs WARN                                         │ │
│  │  ├─ Severity: Any FAIL = stop here                                      │ │
│  │  └─ Decision Logic:                                                     │ │
│  │     ├─ If any FAIL:   → "ISSUES_FOUND" → go to Phase 3                │ │
│  │     ├─ If all WARN:   → "PROCEED" (with warnings)                      │ │
│  │     └─ If all PASS:   → "PROCEED" → skip to Phase 4                   │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│                          ┌─────────┴──────────┐                              │
│                          ▼                    ▼                              │
│        (PROCEED)                     (ISSUES_FOUND)                          │
│          │                              │                                   │
│          └──────────────────────────────┼──────────────────┐                │
│                                         │                  │                │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │ PHASE 3: SELF-HEALING ANALYSIS & ROUTING                    │           │
│  ├──────────────────────────────────────────────────────────────┤           │
│  │                                                              │           │
│  │  For each FAIL/WARN:                                        │           │
│  │  ├─ Issue Diagnostic Engine analyzes:                       │           │
│  │  │  ├─ What failed? (test name, error msg)                 │           │
│  │  │  ├─ Confidence: HIGH (regex match) or LOW (heuristic)   │           │
│  │  │  ├─ Risk level: LOW (typo) or HIGH (security)           │           │
│  │  │  └─ Auto-fixable: YES or NO                             │           │
│  │  │                                                          │           │
│  │  ├─ ROUTING DECISION TREE:                                 │           │
│  │  │  ├─ HIGH confidence + LOW risk  ───┐                    │           │
│  │  │  │   (typo, linting, formatting)   │ ──→ HEALER        │           │
│  │  │  │                                 │    Engineer        │           │
│  │  │  │                                 │    (auto-fix)      │           │
│  │  │  │                                 │                    │           │
│  │  │  ├─ HIGH confidence + HIGH risk  ──┐                    │           │
│  │  │  │   (credential, CVE, test fail)  │ ──→ ESCALATE      │           │
│  │  │  │                                 │    to Human        │           │
│  │  │  │                                 │    (review)        │           │
│  │  │  │                                 │                    │           │
│  │  │  └─ LOW confidence               ─┴──→ ESCALATE        │           │
│  │  │      (analyze manually)                                 │           │
│  │  │                                                          │           │
│  │  └─ Create Healer Tasks or PRs                             │           │
│  │                                                              │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                        │                  │                                  │
│            ┌───────────┴───────────┐      │                                  │
│            ▼                       ▼      ▼                                  │
│     Healer Agent          Escalate       Already                             │
│     (run fixes)           to Human       PROCEED                             │
│            │                 │              │                               │
│            ▼                 ▼              │                               │
│  Re-run Phase 1        Manual Review   Continue ──┐                         │
│            │                 │                    │                         │
│            └─────┬───────────┘                    │                         │
│                  ▼                                │                         │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ PHASE 4: FINAL DECISION                                    │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │                                                            │             │
│  │  After Phase 3 (or if PROCEED from Phase 2):              │             │
│  │  ├─ All Phase 1 checks passed ──→ PROCEED (exit 0) ✅    │             │
│  │  ├─ Warnings present ──────────→ PROCEED (exit 0) ⚠️     │             │
│  │  ├─ Unresolved issues ────────→ WARN (exit 0)            │             │
│  │  └─ High-risk escalations ────→ BLOCK (exit 1) ❌        │             │
│  │                                                            │             │
│  │  Output:                                                  │             │
│  │  ├─ Exit code: 0 (deployment allowed) or 1 (blocked)     │             │
│  │  ├─ Audit trail: .jsonl file with all decisions          │             │
│  │  └─ Summary: Human-readable results                       │             │
│  │                                                            │             │
│  └────────────────────────────────────────────────────────────┘             │
│                            │                                                │
│                            ▼                                                │
│  GitHub Actions CI/CD:                                                     │
│  ├─ Exit 0 ──→ Continue to deploy-prod job ✅                             │
│  └─ Exit 1 ──→ Block deploy-prod (dev already deployed) ❌                │
│                                                                             │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 3: Agent Orchestration & Delegation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    QUALITY GATE ORCHESTRATOR                                │
│                  (runs in GitHub Actions)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
         ┌────────────────────────────────────────┐
         │ Phase 3: Healing Analysis              │
         │ Issue: Hardcoded credential detected   │
         │ Confidence: HIGH, Risk: HIGH           │
         │ Verdict: Must escalate (not auto-fix)  │
         └────────────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
        ┌──────────────────────┐   ┌──────────────────────┐
        │ Would create Healer  │   │ Alert: Escalate to   │
        │ task IF auto-fixable │   │ Security Engineer    │
        │ (not in this case)   │   │ (Principal/Opus)     │
        └──────────────────────┘   └──────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
                    │ (In real production flow, would dispatch     │
                    │  PrincipalEngineer agent for review)         │
                    │                                               │
                    ▼                                               ▼
        ┌──────────────────────────────────┐   ┌──────────────────────────────┐
        │ AGENT TASK CREATED               │   │ HUMAN REVIEW (async)         │
        │ Type: Security Review            │   │ Developer gets GitHub notice │
        │ Model: Claude Opus 4.7           │   │ Sees:                        │
        │ Context: CLAUDE.md + Task info   │   │ - What failed (credential)   │
        │                                  │   │ - Where (config.go:42)       │
        │ Work to do:                      │   │ - How to fix (env vars)      │
        │ 1. Analyze credential exposure   │   │ - Audit trail (.jsonl)       │
        │ 2. Suggest remediation           │   │                              │
        │ 3. Document security impact      │   │ Developer action:            │
        │ 4. Create or approve PR          │   │ 1. Fix locally               │
        │                                  │   │ 2. Push new commit           │
        │ Output: HANDBACK                 │   │ 3. Quality gates re-run      │
        │ - PR with fixes                  │   │ 4. Pass/fail (depends on fix)│
        │ - Audit notes                    │   │                              │
        │ - Recommendation                 │   │                              │
        └──────────────────────────────────┘   └──────────────────────────────┘
                    │
                    ▼ (If PR created and approved)
        ┌──────────────────────────────────┐
        │ HEALER PR MERGE                  │
        │ (not applicable here - requires  │
        │  human decision on credentials)  │
        └──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│         DEVELOPER FIXES LOCALLY & RE-PUSHES (shown earlier)                │
│                                                                             │
│  Developer commits fix: git commit -m "fix(security): use env var"         │
│                                                                             │
│  ▼ QUALITY GATES RE-RUN (same orchestrator, new push)                     │
│  ├─ Phase 1: All checks run again                                          │
│  │  └─ security-secrets: NO CREDENTIAL FOUND ✅                            │
│  │  └─ (all other checks still pass)                                       │
│  ├─ Phase 2: PROCEED (no issues found)                                     │
│  ├─ Phase 3: Skip (no issues to heal)                                      │
│  ├─ Phase 4: PROCEED (exit 0) ✅                                           │
│  │                                                                          │
│  ▼ GITHUB ACTIONS: deploy-prod job now unblocked                          │
│  ├─ Can deploy (no quality gate failures)                                  │
│  └─ Production deployment proceeds ✅                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 4: Quality Skills → Agents Mapping

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         QUALITY SKILLS LAYER                               │
│              (12 reusable skills, all .md files in skills/)                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │ test-unit      │  │ test-integ     │  │ test-e2e       │             │
│  │ (unit tests)   │  │ (db + network) │  │ (playwright)   │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
│                                                                            │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ TESTING SKILLS (4 total)                              │             │
│  │ All run: make test (or Makefile test target)         │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                            │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐         │
│  │ security-deps    │ │ security-secrets │ │ security-scan    │         │
│  │ (CVE scanning)   │ │ (grep patterns)  │ │ (SAST)           │         │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘         │
│                                                                            │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ SECURITY SKILLS (3 total)                             │             │
│  │ Credential detection routed to Security Engineer      │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                            │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐         │
│  │ compliance-req   │ │ compliance-spec  │ │ requirement-map  │         │
│  │ (data schemas)   │ │ (spec validation)│ │ (requirement→code│         │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘         │
│                                                                            │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ COMPLIANCE SKILLS (3 total)                            │             │
│  │ Verifies schema, spec, and requirement mapping        │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                            │
│  ┌──────────────────┐ ┌──────────────────┐                              │
│  │ issue-diagnostic │ │ healer-engineer  │                              │
│  │ (route to agents)│ │ (auto-fix LOW    │                              │
│  │                  │ │  confidence+risk)│                              │
│  └──────────────────┘ └──────────────────┘                              │
│                                                                            │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ SELF-HEALING SKILLS (2 total)                          │             │
│  │ issue-diagnostic routes findings to agents            │             │
│  │ healer-engineer auto-fixes safe issues                │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
        ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
        │ AGENTS.md        │  │ Agent Router │  │ Sub-Agent Types  │
        ├──────────────────┤  ├──────────────┤  ├──────────────────┤
        │ Lists all agent  │  │ Routes per   │  │ Engineer/Senior/ │
        │ types + models:  │  │ complexity:  │  │ Principal by     │
        │                  │  │              │  │ task scope:      │
        │ - Engineer       │  │ LOW      →   │  │ ┌──────────────┐ │
        │   (Haiku)        │  │   Haiku      │  │ │ Haiku: typos,│ │
        │                  │  │              │  │ │ formatting   │ │
        │ - Senior         │  │ MEDIUM   →   │  │ ├──────────────┤ │
        │   (Sonnet)       │  │   Sonnet     │  │ │ Sonnet: logic│ │
        │                  │  │              │  │ │ bugs, perf   │ │
        │ - Principal      │  │ HIGH     →   │  │ ├──────────────┤ │
        │   (Opus)         │  │   Opus       │  │ │ Opus:        │ │
        │                  │  │              │  │ │ security,    │ │
        │ - SecurityEng    │  │ CRITICAL →   │  │ │ architecture │ │
        │   (Opus)         │  │   Opus       │  │ └──────────────┘ │
        │                  │  │              │  │                  │
        │ - DeployEng      │  │ (based on    │  │ Examples:        │
        │   (Sonnet)       │  │  risk, not   │  │ - Typo → Haiku   │
        │                  │  │  just score) │  │ - Logic → Sonnet │
        │ - DataEng        │  │              │  │ - Security → Opus│
        │   (Sonnet)       │  │              │  │                  │
        │                  │  │              │  │                  │
        └──────────────────┘  └──────────────┘  └──────────────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│                       EXAMPLE CREDENTIAL FLOW                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  security-secrets skill detects hardcoded AWS_ACCESS_KEY                  │
│  │                                                                         │
│  ├→ issue-diagnostic-engine analyzes:                                     │
│  │  ├─ HIGH confidence (regex pattern match)                              │
│  │  ├─ HIGH risk (production secret exposure)                             │
│  │  └─ NOT auto-fixable (humans must decide)                              │
│  │                                                                         │
│  └→ ESCALATE to Principal Engineer (Opus) via DELEGATE markup             │
│     │                                                                      │
│     │ Prompt: Review credential exposure, recommend remediation           │
│     │                                                                      │
│     ├→ Agent context includes:                                            │
│     │  ├─ CLAUDE.md (security patterns, ERS architecture)                │
│     │  ├─ Quality gate audit trail (.jsonl)                              │
│     │  ├─ Failing skill output (credential location, pattern)            │
│     │  ├─ Code snippet (context around credential)                       │
│     │  └─ Previous similar findings (if any)                             │
│     │                                                                      │
│     └→ Agent returns HANDBACK:                                            │
│        ├─ Analysis: "Production AWS credential exposed in config.go:42"  │
│        ├─ Risk: "Immediate compromise risk if code is public"            │
│        ├─ Recommendation: "Rotate key, use Secrets Manager + env var"    │
│        ├─ Example fix: (code snippet showing solution)                    │
│        └─ Approval: "Cannot auto-fix; requires developer manual action" │
│                                                                            │
│  Result: Developer sees actionable feedback, fixes locally, re-pushes     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 5: SDLC Gate Sequence (High-Level)

```
Developer          GitHub          Quality Gate      Sub-Agents      Production
   │                 │            Orchestrator         (if needed)        │
   │                 │                  │                  │              │
   ├─ Commit & Push  │                  │                  │              │
   ├────────────────→ │                  │                  │              │
   │                 │                  │                  │              │
   │                 ├─ build-deploy-dev │                  │              │
   │                 ├───────────────────→ dev tests pass   │              │
   │                 │                    dev deployed ✅    │              │
   │                 │                  │                  │              │
   │                 ├─ quality-gate-prod │                  │              │
   │                 ├───────────────────→ Phase 1: Run all checks
   │                 │                    Phase 2: Decision gate
   │                 │                    Phase 3: Analyze issues
   │                 │                    │                  │              │
   │                 │                    │ (if HIGH risk)   │              │
   │                 │                    ├─ Create ticket   │              │
   │                 │                    ├─────────────────→ ESCALATE     │
   │                 │                    │                    (return HANDBACK)
   │                 │                    │← (decision: human fix needed)  │
   │                 │                    │                  │              │
   │                 │    (GitHub notification sent to dev)   │              │
   │                 │  "Quality gate failed: credential"    │              │
   │                 │← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│              │
   │                 │                                       │              │
   │ (Developer fixes locally)                               │              │
   │                                                         │              │
   ├─ Fix + Commit + Push (2nd time)                        │              │
   ├────────────────→ │                  │                  │              │
   │                 │                  │                  │              │
   │                 ├─ build-deploy-dev │                  │              │
   │                 ├───────────────────→ ✅ Pass           │              │
   │                 │                  │                  │              │
   │                 ├─ quality-gate-prod │                  │              │
   │                 ├───────────────────→ ✅ All pass       │              │
   │                 │                    exit code 0       │              │
   │                 │                  │                  │              │
   │                 ├─ deploy-prod (now unblocked)         │              │
   │                 ├───────────────────→ Deploy           │              │
   │                 │                    Tag release       │              │
   │                 │                    exit code 0       │              │
   │                 │                  │                  │              │
   │                 │                  │                  │              │
   │← ─ ─ ─ ─ Deployment complete notification ─ ─ ─ ─ ─ →│
   │                 │                  │                  │ ✅ PROD
   │                 │                  │                  │ deployed
   │                 │                  │                  │
```

---

## Diagram 6: Audit Trail Structure

```
quality-gate-audit-<SESSION_ID>.jsonl

Each line = JSON event (one per phase + skill)

Entry 1 (Phase 1 kickoff):
{
  "timestamp": "2026-04-28T14:32:15Z",
  "session_id": "a1b2c3d4-e5f6",
  "phase": "phase_1",
  "event": "started",
  "details": {"env": "prod", "service": "{service-name}"}
}

Entry 2-7 (Skill results):
{
  "timestamp": "2026-04-28T14:32:45Z",
  "session_id": "a1b2c3d4-e5f6",
  "phase": "phase_1",
  "skill": "security-secrets",
  "status": "FAIL",
  "details": {
    "issue": "hardcoded_credential",
    "pattern": "AKIA[0-9A-Z]{16}",
    "location": "config.go:42",
    "severity": "CRITICAL"
  }
}

Entry 8 (Phase 2 decision):
{
  "timestamp": "2026-04-28T14:33:00Z",
  "session_id": "a1b2c3d4-e5f6",
  "phase": "phase_2",
  "status": "ISSUES_FOUND",
  "details": {
    "failed_skills": ["security-secrets"],
    "decision": "route_to_phase_3"
  }
}

Entry 9 (Phase 3 diagnostic):
{
  "timestamp": "2026-04-28T14:33:15Z",
  "session_id": "a1b2c3d4-e5f6",
  "phase": "phase_3",
  "status": "ESCALATE",
  "details": {
    "issue_id": "sec-001",
    "confidence": "HIGH",
    "risk_level": "HIGH",
    "auto_fixable": false,
    "routed_to": "SecurityEngineer",
    "agent_model": "opus"
  }
}

Entry 10 (Phase 4 final):
{
  "timestamp": "2026-04-28T14:33:30Z",
  "session_id": "a1b2c3d4-e5f6",
  "phase": "phase_4",
  "status": "ESCALATE",
  "decision": "BLOCK",
  "exit_code": 1,
  "details": {
    "deployment_target": "prod",
    "blocking_reason": "unresolved_security_issue",
    "notification_sent": true
  }
}

Usage in Phase 5.10:
- Analyze success patterns: Which skills catch real issues? False positive rate?
- Improvement loop: Refine routing rules based on outcomes
- Metrics: Track escalation rates, human review times, Healer success rate
```

---

## How Everything Connects

### Flow: CODE → SKILLS → AGENTS → DEPLOYMENT

```
1. Developer writes code with hardcoded credential
   ↓
2. Commits + pushes to main
   ↓
3. GitHub Actions triggers build-deploy-dev + quality-gate-prod
   ↓
4. Quality Gate Orchestrator (quality-gate-orchestration.sh) runs:
   Phase 1: 12 skills run in parallel (including security-secrets)
   Phase 2: Initial decision gate (ISSUES_FOUND)
   Phase 3: Diagnostic engine routes to agent (HIGH confidence + HIGH risk)
   Phase 4: Final decision (ESCALATE, exit code 1)
   ↓
5. Orchestrator creates DELEGATE task for SecurityEngineer agent (Opus)
   Context includes: CLAUDE.md, audit trail, code snippet
   ↓
6. Agent analyzes, returns HANDBACK:
   "Credential exposed → rotate key → use Secrets Manager"
   ↓
7. Developer reads notification, sees specific fix guidance
   ↓
8. Developer fixes locally, commits, pushes
   ↓
9. quality-gate-prod runs again:
   Phase 1: All skills PASS (no credential detected)
   Phase 4: PROCEED (exit code 0)
   ↓
10. deploy-prod job unblocks, production deployment proceeds
    Audit trail recorded: detection → escalation → fix → re-validation → deploy
```

---

## Key Takeaways

**Quality skills** are reusable, callable functions defined in `.md` files.

**Orchestrator** (shell script) calls skills, evaluates results, routes to agents.

**Agents** (via DELEGATE + HANDBACK) handle complex logic:
- Security reviews (Opus)
- Typo fixes (Haiku)
- Performance tuning (Sonnet)

**Audit trail** (`.jsonl`) captures every decision for Phase 5.10 improvement loop.

**Developer experience**:
- Local gates fast-fail (30s-2min)
- GitHub Actions gates block bad deploys (prevents prod outages)
- Clear feedback loops (know what failed, why, how to fix)
