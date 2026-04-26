---
name: ERS Architecture Skills Index
type: index
last_updated: 2026-04-27 (planning & workflow skills added)
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

## Planning & Workflow Standards

### 4. **planning-standard.md** — TODO.md-Only Planning Enforcement
- **Purpose**: Centralizes all planning documentation in TODO.md files; prevents scatter of plan.md or separate planning docs
- **Key rules**:
  - All planning work goes in TODO.md (service or workspace level)
  - Never create `plan.md`, `PLAN.md`, or separate planning documents
  - Structure: Status, Goals, Approach, Tasks, Success Criteria, Notes
  - Link TODO.md tasks from code PRs and commits
- **Who uses it**: All engineers, when starting new initiatives
- **When to reference**: Before creating planning docs, during code review, when tracking initiative progress

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

## Current Compliance Status (2026-04-27)

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

