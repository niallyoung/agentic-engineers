---
name: ERS Architecture Skills Index
type: index
last_updated: 2026-04-28 (Phase 5 Quality Engineer + Self-Healing skills complete)
---

# ERS Architecture & Enforcement Skills

This index catalogs architectural decision patterns and enforcement skills for the ERS platform.

## Configuration & Dependency Management

### 1. **{service-name}.md** — The Baseline Standard
- **Purpose**: Defines how all ERS services handle configuration, environment variables, and cross-service dependencies
- **Key rules**:
  - REQUIRED dependencies fail loudly if missing
  - OPTIONAL features use explicit empty strings with documented rationale
  - No silent defaults
  - No quotes in environment files
  - Makefile exports all variables automatically
- **Who uses it**: All engineers, during code review and architecture discussions
- **When to reference**: Anytime you touch configuration, environment variables, or cross-service calls

### 2. **{service-name}.md** — Audit & Verification Checklist
- **Purpose**: Provides tools and checklists to verify services comply with the standard
- **Includes**:
  - Quick audit command that checks all 8 services
  - Detailed checklist for each service
  - Automated fixes for common issues
  - Audit report template
- **Who uses it**: Quality Engineers, during code review or pre-deployment
- **When to audit**: After CDK changes, Makefile modifications, before deployment
- **Delegable to**: Quality Engineer, Lead Engineer (full audit + fixes)

### 3. **{service-name}.md** — Delegation Pattern & Common Fixes
- **Purpose**: Provides the DELEGATE/HANDBACK format for fixing configuration issues
- **Includes**:
  - How to delegate to sub-agents
  - Common fixes with before/after examples
  - Verification checklist
  - HANDBACK format for completion
- **Who uses it**: Orchestrator (delegates to QE/LE), QE/LE (executes fixes)
- **When to use**: When CICD fails or code review finds compliance gaps

## Planning, Execution & Implementation Workflow

### 4. **planning-standard.md** — TODO.md-Only Planning Enforcement
- **Purpose**: Centralizes all planning documentation in TODO.md files; prevents scatter of plan.md or separate planning docs
- **Key rules**:
  - All planning work goes in TODO.md (service or workspace level)
  - Never create `plan.md`, `PLAN.md`, or separate planning documents
  - Structure: Status, Goals, Approach, Tasks, Success Criteria, Notes
  - Link TODO.md tasks from code PRs and commits
- **Who uses it**: All engineers, when starting new initiatives
- **When to reference**: Before creating planning docs, during code review, when tracking initiative progress

### 5. **plan-iterate.md** — Multi-Stage Expert Review for Plan Refinement
- **Purpose**: Delegate plan iteration through Senior → Principal → Security engineers (or custom review chain)
- **Pattern**: Each stage builds on prior feedback; minimizes tokens, maximizes domain expertise
- **Stages**: Senior Engineer (feasibility), Principal Engineer (strategy), Security Engineer (risks)
- **Handoff format**: DELEGATE with role-specific prompts for each stage
- **Output**: Refined plan in TODO.md + REVIEW-*.md documents committed to git
- **Who uses it**: Orchestrator (when plans need refinement before implementation)
- **When to use**: Major features, cross-service initiatives, infrastructure redesigns, security-critical work
- **Updated**: Lessons learned from spec-extract included; schema/ADR decisions flagged as load-bearing

### 6. **engineer-execution.md** — Base-Level Engineer Task Execution & Escalation
- **Purpose**: Enable Engineers to execute tasks with clear escalation paths (Engineer → Lead → Principal/Security)
- **Pattern**: Reuses the multi-stage review pattern from plan-iterate; escalates only when blocked
- **Roles**: Engineer (Sonnet) executes; Lead (Sonnet/Opus) unblocks; Principal/Security escalate for decisions
- **Handoff format**: TASK_ASSIGNMENT with clear success criteria and effort estimate
- **Escalation triggers**: Design ambiguity, external dependency, effort exceeded, security concern, scope unclear
- **Metrics**: Time to completion, escalations per task, success criteria met, estimation accuracy
- **Who uses it**: Orchestrator assigns tasks; Engineers execute with escalation as needed
- **When to use**: Executing approved plans (Phase 1 of implementation-workflow.md)

### 7. **implementation-workflow.md** — End-to-End Plan → Execute → Review → Finalize
- **Purpose**: Complete workflow combining plan iteration, task execution, and final reviews
- **Phases**:
  1. Plan Iteration (3-4 hours): Senior → Principal → Security reviews, Orchestrator integrates
  2. Task Execution (variable): Engineer executes tasks, escalates blockers to Lead/Principal/Security
  3. Final Review (1-2 hours): Senior + Principal review implementation vs. plan intent
  4. Security Review (0.5-1 hour, if needed): Security spot-checks threat mitigations
  5. Finalization (15-30 min): Orchestrator archives plan, documents lessons learned
- **Timeline**: ~1.5 weeks for typical mid-size plan (4-5 days Engineer work)
- **Metrics**: Per-phase time, escalations, review feedback, task estimation accuracy
- **Lessons learned template**: Documents reusable patterns and improvements for next cycle
- **Who uses it**: Orchestrator, Engineers, Lead, Principal, Security
- **When to use**: Any significant implementation (new feature, refactoring, infrastructure, cross-service work)

## Operations & Automation

### 5. **cleanup.md** — Post-Task Cleanup Automation
- **Purpose**: Automates cleanup of temporary files, old plans, and consolidates documentation after task completion
- **Includes**:
  - 4-phase cleanup (plans, temp files, docs, verification)
  - Pre-push checklist integration
  - Consolidation rules for orphaned .md files
- **Who uses it**: All engineers, before every `git push`
- **When to run**: Integrated into pre-push workflow or manual execution: `bash ~/.agents/agentic-engineers/skills/cleanup.sh`

### 6. **voice-notifications.md** — Context-Aware Voice Notifications
- **Purpose**: Provides voice cues via `osascript` with context-aware phrases (vs hardcoded commands)
- **Includes**:
  - When to use "watching cicd", "waiting", "hmm" phrases
  - Integration with skill-based notifications (not settings.json)
  - Token conservation guidance
- **Who uses it**: CI/CD monitors, long-running task watchers
- **When to use**: When implementing monitoring skills that need user attention signaling

### 7. **cicd-monitoring.md** — Token-Conserving Build Monitoring
- **Purpose**: Monitoring long-running CICD jobs with 120-second sleep intervals vs active polling
- **Includes**:
  - Why 120s (within Anthropic 5-min cache TTL)
  - Token impact analysis (85% savings vs polling)
  - Integration with agentic-engineers workflow
  - Multi-service monitoring patterns
- **Who uses it**: Orchestrator or monitoring agent
- **When to use**: When watching GitHub Actions, long deploys, or multi-service builds

## Specification & Patterns (In Planning)

### 8. **spec-extract.md** — Software Specification Extraction Skill (Planned)
- **Status**: Planning phase (see `{service-name}/TODO.md: spec-extract`)
- **Purpose**: Scan multi-repo microservices platforms; extract and catalog reusable patterns
- **Target output**: `{service-name}/specs/` with pattern registry, compliance audits
- **Phases**: Research, pattern extraction, catalog generation, compliance framework, documentation
- **Who will use it**: Lead engineers, compliance auditors, onboarding new services
- **Complementary skill**: `spec-audit.md` (validates repos against extracted specs)

## Security Verification (Phase 5 — Quality Engineer)

### **security-semantic-scan.md** — Claude-Based Data Flow Analysis
- **Purpose**: Semantic security scanning that traces data flows across components to find multi-component vulnerabilities that pattern matching misses (e.g., JWT scope checked in API Gateway but not in Lambda handler)
- **Input**: `service_path`, `focus_areas` (auth, data_flow, crypto), `verify_findings`
- **Output**: Findings with severity, data flow chain, adversarial verification status, false positive count
- **Severity**: HIGH (privilege escalation, injection), MEDIUM (weak crypto), LOW (logging)
- **Escalation**: ALL findings require Security Engineer review before action — never auto-fix
- **Called by**: `quality-gate-orchestration` (security scan phase)
- **Model**: Claude Opus recommended for analysis steps

### **security-dependency-scan.md** — CVE Scanning for Go / Node / Rust
- **Purpose**: Detect known CVEs in third-party dependencies; auto-detects language and runs appropriate scanner
- **Scanners**: `govulncheck` (Go), `npm audit` (Node), `cargo audit` (Rust), `pip-audit` (Python)
- **Input**: `service_path`, `fail_on_critical`, `fail_on_major`, `fix_available_only`
- **Output**: Vulnerability list with CVE ID, package, installed version, fix version, gate result
- **Gate**: BLOCK on critical, WARN on major, LOG on minor
- **Escalation**: Critical blocks deployment; major requires Security Engineer review
- **Called by**: `quality-gate-orchestration` (parallel with other security scans)

### **security-secret-detection.md** — Hardcoded Secret Detection
- **Purpose**: Detect hardcoded AWS credentials, API keys, private keys, JWT tokens before commit or deployment
- **Input**: `scan_source` (git_diff, file, commit_range), `commit_hash`, `fail_on_found`
- **Output**: Detections with type, file, line, redacted match, gate result
- **Severity**: Always CRITICAL — no lower severity for secrets
- **Gate**: BLOCK on any detection (regardless of `fail_on_found`)
- **Integration**: Designed to run in `pre-commit` and `pre-push` git hooks
- **Escalation**: Immediate rotation required; never delegate to Healer

## Testing Orchestration (Phase 5 — Quality Engineer)

### **test-unit-orchestration.md** — Unit Test Discovery & Execution
- **Purpose**: Discover, execute, and report on unit tests; parse coverage output for gate decisions
- **Input**: `service_path`, `test_filter` (optional glob), `coverage_threshold`
- **Output**: Tests passed/failed, coverage %, failed test list, mutation recommendations
- **Coverage gate**: PASS if >= threshold (default 80%), WARN if below
- **Called by**: `quality-gate-orchestration` (testing phase, parallel execution)

### **test-integration-orchestration.md** — Integration Test Orchestration
- **Purpose**: Run integration tests with ERS service mocking (DynamoDB, SNS, EventBridge)
- **Input**: `service_path`, `environment` (test/staging/dev), `test_filter`
- **Output**: Integration tests passed/failed, mocks used, execution time
- **Mocking**: LocalStack for DynamoDB/SNS/SQS, serverless-offline for Lambda
- **Called by**: `quality-gate-orchestration` (testing phase, parallel execution)

### **test-e2e-orchestration.md** — Playwright E2E Test Orchestration
- **Purpose**: Filter and execute Playwright E2E tests by scenario name; capture video/traces on failure
- **Input**: `scenario_filter` (optional: "login", "create_event"), `headless`, `parallel_workers`
- **Output**: Scenarios run/passed/failed, execution time, trace files if failures
- **Cost**: High (run only pre-deployment, not per-commit)
- **Called by**: `quality-gate-orchestration` (if `skip_e2e=false`)

### **test-business-logic.md** — Business Logic & State Machine Testing
- **Purpose**: Parametric testing for edge cases, state transitions, data interactions
- **Input**: `service_path`, `business_logic_spec` (requirements), `state_machine_transitions`
- **Output**: Edge cases tested, state transitions covered, uncovered transitions flagged
- **Examples**: User role transitions (member→admin→disabled), event status flows, concurrent writes
- **Called by**: `quality-gate-orchestration` (testing phase, parallel execution)

## Compliance & Requirements (Phase 5 — Quality Engineer)

### **requirement-mapping.md** — Requirement Traceability Mapping
- **Purpose**: Map requirements → test cases → code; calculate coverage %; identify unmapped requirements
- **Input**: `service_path`, `spec_file` (requirement spec)
- **Output**: Requirement coverage %, mapping matrix, unmapped requirements, orphaned code
- **Gate**: Informational (no gate decision, reports only)
- **Called by**: `quality-gate-orchestration` (compliance phase)

### **requirement-verification.md** — Pre-Deployment Requirement Gate
- **Purpose**: Pre-deployment gate: verify all requirements have passing tests
- **Input**: `service_path`, `deployment_target` (dev/staging/prod)
- **Output**: Requirements tested, requirements all passing, gate result (PROCEED/WARN/BLOCK)
- **Strictness**: Prod requires 100% requirement coverage, dev allows partial
- **Called by**: `quality-gate-orchestration` (compliance phase)

### **spec-compliance-verification.md** — Spec Compliance Validation
- **Purpose**: Verify code implementation complies with extracted architectural specs
- **Input**: `service_path`, `spec_dir` ({service-name}/specs)
- **Output**: Spec compliance %, deviations detected, severity per deviation
- **Checks**: Makefile pattern, CDK structure, event versioning, auth flow, config standard, GitHub Actions, replay mode
- **Called by**: `quality-gate-orchestration` (compliance phase)

## Self-Healing Feedback Loop (Phase 5 — Quality Engineer)

### **issue-diagnostic-engine.md** — Root Cause Analysis & Confidence Scoring
- **Purpose**: Diagnose quality gate failures; assess confidence (HIGH/LOW) and risk (LOW/HIGH)
- **Input**: `failure_log` (test/security/config), `failure_type`
- **Output**: Root cause category, confidence, risk level, suggested fix, healer_eligible flag
- **Categories**: dependency, configuration, test_flakiness, logic, infrastructure, security
- **Routing**: HIGH confidence + LOW risk → Healer eligible; otherwise → escalate to human
- **Called by**: `quality-gate-orchestration` (self-healing phase, per issue)

### **healer-engineer.md** — Autonomous Issue Fixing & PR Creation
- **Purpose**: Auto-fix low-risk, pattern-matchable issues; create PR with optional auto-merge
- **Input**: `diagnostic` result (must have confidence=HIGH, risk_level=LOW)
- **Allowed fixes**: Missing env var, dependency patch, flaky test, lockfile stale, import path wrong
- **Output**: PR created with audit trail, auto-merge status if applicable
- **Constraints**: Single file change, no multi-file refactoring, conservative auto-merge rules
- **Called by**: `quality-gate-orchestration` (self-healing phase, after diagnostic)

## Master Orchestration (Phase 5 — Quality Engineer)

### **quality-gate-orchestration.md** — Master Quality Gate Orchestrator
- **Purpose**: Coordinate all 12 quality skills in comprehensive pre-deployment verification with self-healing loop
- **Input**: `service_path`, `deployment_target` (dev/staging/prod), `skip_e2e`, `max_heal_attempts`
- **Output**: Structured gate decision (PROCEED/WARN/BLOCK/ESCALATE), audit trail, report saved to S3
- **Workflow**: 
  1. PHASE 1: Run all 12 skills in parallel (testing, security, compliance)
  2. PHASE 2: Check if all green; if yes → PROCEED; if no → PHASE 3
  3. PHASE 3: Self-healing loop (diagnostic → healer or escalate)
  4. PHASE 4: Final gate decision with deployment readiness
- **Strictness by target**: prod (all requirements, 100% coverage) > staging > dev
- **Called by**: GitHub Actions, Orchestrator agent, pre-deployment hooks

## Roles (Phase 5 — Quality Engineer Specialization)

### **Healer Engineer** (`roles/healer-engineer.md`)
- **Purpose**: Autonomous agent that auto-fixes low-risk quality issues
- **Responsibilities**: Fix missing env vars, dependency patches, flaky tests, lockfiles, import paths
- **Constraints**: Only acts on HIGH confidence + LOW risk diagnostics; escalates high-risk issues
- **Auto-fix types**: Configuration missing, dependency patch bump, test flakiness, lockfile regeneration, import path wrong
- **NO auto-fix**: Security issues, logic bugs, architecture changes, multi-file refactoring
- **Success metric**: >70% of detected issues should be auto-fixable
- **Model**: Claude Sonnet (cost-effective autonomous execution)

### **Quality Engineer** (updated)
- **Responsibilities**: Orchestrate all quality gates, coordinate self-healing loop, make final deployment decisions
- **Skills used**: All 12 quality skills + orchestrator + diagnostic engine + healer routing
- **Decision authority**: PROCEED/WARN/BLOCK/ESCALATE on deployments
- **Escalation paths**: Lead (logic issues) → Principal (architecture) → Security (findings)

## Monitoring & Continuous Improvement (Phase 5.10)

### **PHASE-5.10-MONITORING-PLAN.md** — Comprehensive Monitoring Implementation Plan
- **Status**: Phase 5.10 IN PROGRESS (2026-04-28)
- **Purpose**: Build observability infrastructure for quality gates; measure Healer effectiveness; enable Level 2→Level 3 graduation
- **5 Phases**:
  1. Audit trail centralization (CloudWatch Logs)
  2. CloudWatch metrics and dashboards
  3. Healer success rate tracking
  4. Confidence score calibration
  5. Continuous improvement feedback loop
- **Deliverables**: Plan document, metrics analyzer tool, graduation checklist, CloudWatch queries

### **healer-metrics-analyzer.py** — Audit Log Analysis Tool
- **Purpose**: Analyze quality gate audit logs to measure Healer success rates and readiness for Level 3
- **Input**: Audit logs directory, days to analyze (default: 30)
- **Output**: JSON report with:
  - Healer success rate (% of fixes that pass re-validation)
  - Auto-merge rate (% of successful fixes auto-merged)
  - Escalation rate (% escalated to humans)
  - Phase success rates by phase
  - Failure patterns by issue type
  - Level 3 readiness assessment (5 criteria)
- **Usage**: `./healer-metrics-analyzer.py --days 30 --pretty`
- **Frequency**: Run monthly or on-demand for readiness assessment

### **LEVEL-3-GRADUATION-CHECKLIST.md** — Level 2→Level 3 Readiness Criteria
- **Purpose**: Define and validate 5 success criteria for graduating from intelligent routing (Level 2) to autonomous healing (Level 3)
- **5 Criteria**:
  1. Healer success rate ≥ 70% (empirical, from metrics analyzer)
  2. Auto-merge rate ≥ 50% (empirical)
  3. Escalation rate ≤ 30% (empirical)
  4. Confidence calibration error < 5% (predicted vs actual)
  5. Zero critical incidents from Healer fixes (30-day monitoring)
- **Pre-rollout validation**: Security review, process review, team sign-off
- **Rollout plan**: Phased (1 service → 3 services → all services)
- **Failure recovery**: Documented procedures for rollback scenarios

### **cloudwatch-queries.md** — CloudWatch Logs Insights Query Reference
- **Purpose**: Reusable CloudWatch Logs Insights queries for audit trail analysis
- **12 Queries**:
  - Quality gate success rate by service
  - Phase success rates
  - Healer intervention frequency
  - Execution time trends
  - Failure pattern analysis
  - Confidence score calibration
  - Session duration
  - Healer success rate
  - Issue type and confidence breakdown
  - Daily metrics summary
  - Anomaly detection (failure spikes)
  - Healer PR merge rate
  - Service reliability ranking
- **Usage**: Copy/paste into CloudWatch Logs Insights UI or integrate into scheduled reports

### **setup-cloudwatch-monitoring.sh** — CloudWatch Infrastructure Setup
- **Purpose**: One-time setup script to create CloudWatch monitoring infrastructure
- **Creates**:
  - CloudWatch Logs group: `/ers/quality-gates/audit-trail`
  - Log streams for all 7 services × 2 environments (dev, prod)
  - 30-day retention policy
  - CloudWatch Dashboard: "QualityGatesMonitoring" with 5 widgets
- **Usage**: `./setup-cloudwatch-monitoring.sh {service-name} ap-southeast-2`
- **Idempotent**: Safe to run multiple times (skips existing resources)

### **PHASE-5.10-IMPLEMENTATION-SUMMARY.md** — Current Progress & Timeline
- **Status**: Phase 5.10 (1.5 / 2-3 days complete, 50%)
- **Completed**:
  - Monitoring plan (5-phase breakdown)
  - Healer metrics analyzer tool
  - Level 3 graduation checklist
  - CloudWatch queries reference
  - CloudWatch integration in quality-gate-orchestration.sh
  - CloudWatch setup automation script
- **Pending**:
  - AlertManager rules for escalation
  - Scheduled weekly metrics job
  - 2-3 weeks of empirical data collection
  - Level 3 readiness assessment (end of May 2026)
- **Next phase**: Phase 5.11 (Level 3 rollout) once metrics meet 5 criteria

## Current Compliance Status (2026-04-28)

| Service | Makefile | .env Files | CDK | GitHub Actions | Status |
|---------|----------|-----------|-----|----------------|--------|
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ✅ | ✅ | ✅* | ✅ | **COMPLIANT** (1 optional with comment) |
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ✅ | ✅ | ✅ | ✅ | **COMPLIANT** |
| {service-name} | ❌ | ✅ | ✅ | ❌ | **NEEDS FIXES** (likely deprecated) |

**Legend**: ✅ = Compliant | ❌ = Needs fixes | ✅* = Correct with explicit comments

## How to Use These Skills

### As an Engineer (During Development)
1. Before writing configuration code, read `{service-name}.md`
2. Ask yourself: "Is this REQUIRED or OPTIONAL?"
3. Document the answer explicitly in code comments
4. Never use silent defaults

### As a Code Reviewer
1. Use `{service-name}.md` checklist
2. Verify every configuration change is explicit and documented
3. If non-compliant, flag it before approval

### As Quality Engineer (CICD Failure Response)
1. When a CICD build fails, check the error message
2. If it's configuration-related, investigate using `{service-name}.md`
3. Use `{service-name}.md` to delegate fixes to sub-agent
4. Verify fixes pass all checks before signing off

### As Orchestrator (Delegating Work)
1. Detect configuration compliance gap (failed CICD or code review)
2. Use DELEGATE format from `{service-name}.md`
3. Assign to Quality Engineer or Lead Engineer
4. They execute fixes, run verification, HANDBACK
5. You integrate and deploy

## Architecture Decisions Recorded Here

These skills encode decisions made during 2026-04-27 CICD incident:

**The Problem**: 
- {service-name} #41 failed with "Unable to fetch parameters [/dev-{service-name}/APIUrl]"
- Root cause: Missing explicit handling of optional vs required dependencies
- Symptom: Code had silent defaults (empty strings) with no documentation

**The Solution**:
- Establish clear standard for REQUIRED (fail loudly) vs OPTIONAL (explicit + documented)
- Audit all 8 services against standard (7/8 compliant, 1 deprecated)
- Create enforcement skills for QE to delegate fixes via agentic-engineers
- Register in skills index for reuse

**Why This Matters**:
- Operators can't debug failures if configuration handling is silent
- Cross-service dependencies must be explicit
- Failing loudly is better than failing silently in production
- Architectural consistency prevents future surprises

## Related Architecture Patterns

These skills assume and build on:
- **{service-name}**: Standard Makefile pattern (ENV_NAME, -include, export)
- **{service-name}**: Lambda handler patterns (startup validation, graceful degradation)
- **{service-name}**: CDK patterns (3-tier stacks, SSM references)
- **{service-name}**: Local quality gates (make verify, pre-commit hooks)

See `~/git/ers/CLAUDE.md` and `~/git/ers/{service-name}/` for other architectural patterns.

## Workflow Integration

When integrating into agentic-engineers workflows:

1. **Orchestrator** detects CICD failure or code review gap
2. **Orchestrator** reads this index to understand the standard
3. **Orchestrator** uses `{service-name}.md` to DELEGATE
4. **Quality Engineer** reads standard + enforcement guide
5. **Quality Engineer** executes fixes, runs verification
6. **Quality Engineer** HANDBACK with metrics
7. **Orchestrator** integrates and confirms deployment green

## Quarterly Review

These skills should be reviewed quarterly:
- [ ] Audit all 8 services (use `{service-name}.md` audit command)
- [ ] Update compliance table above
- [ ] Add any new architectural patterns discovered
- [ ] Update CLAUDE.md if standards change
- [ ] Ensure all engineers have read the standard

**Last full audit**: 2026-04-27
**Next scheduled**: 2026-07-27


---

## Framework Lifecycle Skills

### repo-init — Repository Initialization
- **Skill:** `src/skills/repo-init/SKILL.md`
- **Purpose:** Bootstrap new repositories with agentic-engineers framework
- **Role:** Senior Engineer
- **Model:** claude-sonnet-4.6
- **Features:**
  - 8-phase initialization workflow
  - Repository analysis (language, package manager, CI/CD)
  - SPEC.md generation with conservative defaults
  - Directory structure bootstrap (agents/, skills/, tests/, docs/)
  - Housekeeping (.gitignore, README.md patches)
  - Framework artifact copy
  - Compatibility validation (Claude, GPT-5, local models)
  - TODO.md initialization with conditional items
  - Documentation generation (ONBOARDING.md, QUICK-START.md, AGENTS.md)
- **Idempotent:** Yes (blocked by INIT-COMPLETE.yaml marker)
- **Dry-run:** Yes (`--dry-run` flag)
- **Dependencies:** agent-creator (scaffold), spec-management (SPEC.md lifecycle)
- **Added:** 2025-05-09
