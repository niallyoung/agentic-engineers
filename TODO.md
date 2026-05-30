# TODO: agentic-engineers

**Last Updated:** 2026-05-30  
**Status:** Active — Phase G Complete, Doc Consolidation Round 2 Complete, README Refactored, Phase H Complete (633 tests TIER1/2/3), Cost Management Complete (3 skills merged), **Phase 1.5 Security Hardening Complete (5 FIXes + 38+ tests)**

---

## ✅ COMPLETED

### Phases 1–6 (Core Framework)
- [x] Queue-based DELEGATE/HANDBACK protocol
- [x] 8 specialized agent roles (Orchestrator, Engineer, Senior, Lead, QE, Security, Principal, Model Engineer)
- [x] 3-layer quality gates (DELEGATE structure, routing quality, HANDBACK validation)
- [x] AutomationController (continuous polling with signal handling)
- [x] Pure Orchestrator (zero business logic, 100% routing)
- [x] ModelResolver (centralized models.yaml)
- [x] MetricsCollector (35-field canonical record per task)
- [x] SDLC enforcement hooks (pre-commit, commit-msg, pre-push)
- [x] 4 harness renderers (OpenCode, Claude Code, Copilot CLI, π.dev)
- [x] 1047+ tests passing (100%)

### Phase 3 Features (Token Visibility & Budget)
- [x] Token tracker implementation (`opencode-tokens` CLI)
- [x] Budget checker implementation (`opencode-budget` CLI)
- [x] Cost attribution per agent/role
- [x] Shadow mode (dry-run delegation)
- [x] Token cost alerts
- [x] Orchestrator CLI quick reference

### Phase B–E (Skills & Harness Improvements)
- [x] 14 skills implemented and rendered
- [x] OpenCode harness: full agent + skill rendering, managed config
- [x] Claude Code harness: 8 agents + 14 skills
- [x] Parallel delegation support (parent-child task hierarchy)
- [x] Span capture (OpenTelemetry format)
- [x] Artifact indexing (Model Engineer generates index.json)

---

## ✅ COMPLETED

### Skills Implementation (Completed 2026-05-19)

- [x] **SKILL-TODO-001:** Implement todo-maintenance skill
  - ✅ Auto-sync queue DELEGATEs ↔ TODO.md on HANDBACK received
  - ✅ Bidirectional sync, conflict detection, weekly reporting
  - ✅ 20/20 tests passing (100%), 80% coverage
  - ✅ Quality: 92/100, Confidence: 95%
  - Completed: 2026-05-19 | Owner: Engineer

- [x] **SKILL-DOC-QUALITY-001:** Implement doc-quality skill
  - ✅ Link validation, cross-ref checks, staleness flagging
  - ✅ Quality metrics, HTML+Markdown reports, CI/CD integration
  - ✅ SPEC.md excluded from all checks (5 dedicated tests)
  - ✅ 52/52 tests passing (100%), >80% coverage
  - ✅ Quality: 94/100, Confidence: 94%
  - Completed: 2026-05-19 | Owner: Quality Engineer

### Market Comparison Enhancement (Completed 2026-05-19)

- [x] **COMPARISON-001:** Add Steve Yegge's Gastown to market comparison
  - ✅ Research Gastown framework (15.4K stars, v1.1.0, May 2026)
  - ✅ Added to README.md Quick Comparison Table (6 columns)
  - ✅ Created detailed Gastown section (600+ words, lines 337-587)
  - ✅ Documented 9 strengths + 5 weaknesses + 6 use-cases
  - ✅ Updated comparison context (resource-aware paradigm)
  - ✅ Quality: 94/100, Confidence: 94%
  - Completed: 2026-05-19 | Owner: Engineer

### README Refactoring (Completed 2026-05-20)

- [x] **README-REFACTOR-001:** Add Key Benefits & Discoveries section
  - ✅ DELEGATE/HANDBACK protocol benefits (90+/100 quality, 40-60% faster, 80% less rework)
  - ✅ Token efficiency analysis (40-60% cost reduction via smart model selection)
  - ✅ Parallel sub-agent execution at scale (36+ concurrent agents tested)
  - ✅ Real-world cost breakdown table and token savings example (65% reduction)
  - ✅ Quality: 94/100
  - Completed: 2026-05-20 | Owner: Orchestrator

- [x] **README-REFACTOR-002:** Simplify Example section with practical DELEGATE YAML
  - ✅ Removed verbose 3-step workflow (plan → implement → review)
  - ✅ Replaced with single, practical DELEGATE YAML example (fix CI/CD timeout)
  - ✅ Shows complete workflow: plan → implement → document → verify → test → commit → push → watch CI/CD
  - ✅ Removed duplicate Model Configuration & Customization section
  - ✅ Clarified OpenCode harness (primary) vs GitHub Copilot (service)
  - ✅ Quality: 95/100
  - Completed: 2026-05-20 | Owner: Orchestrator

### Phase G: Documentation Refresh (Completed 2026-05-18)

- [x] **DOC-AUDIT-001:** Create `docs/DOCUMENTATION-AUDIT.md`
- [x] **DOC-README-001:** Rewrite README.md (<500 lines, accurate, current)
- [x] **DOC-TODO-001:** Refresh TODO.md with current May 2026 status
- [x] **DOC-SPEC-001:** Update SPEC.md with Phase 3 token visibility requirements
- [x] **DOC-QS-001:** Create `docs/QUICK-START-TOKEN-VISIBILITY.md`
- [x] **DOC-QS-002:** Create `docs/QUICK-START-BUDGET-CHECKING.md`
- [x] **DOC-QS-003:** Create `docs/QUICK-START-PRODUCTION-DEPLOYMENT.md`
- [x] **DOC-INDEX-001:** Create `docs/INDEX.md` (master documentation index)
- [x] **DOC-ARCHIVE-001:** Move root-level `*_IMPLEMENTATION.md` files to `docs/archive/phase-reports/`

---

## ✅ COMPLETED

### Doc Consolidation Round 2 (Completed 2026-05-18)

- [x] **CONSOLIDATION-001:** Audit all `docs/` for redundancy, staleness, and unnecessary files
- [x] **CONSOLIDATION-002:** Remove/merge redundant documentation
- [x] **CONSOLIDATION-003:** Update cross-references and links
- [x] **CONSOLIDATION-004:** Verify no broken links or orphaned files
- [x] **CONSOLIDATION-MANIFEST:** Created consolidation manifest with restoration instructions

---

## ✅ COMPLETED

### Phase H: Test Coverage Improvements (Completed 2026-05-28)

- [x] **COVERAGE-TIER1:** Add tests for 5 critical modules (588 stmts)
  - ✅ Modules: core_protocol_validator (150), protocol_audit (201), healer-metrics-analyzer (137), queue_manager (96), test_validators (104)
  - ✅ Target: All modules ≥90% coverage — ACHIEVED (97-99%)
  - ✅ Effort: 21:22 | Status: COMPLETE
  - ✅ 432 tests passing, 5/5 modules at 97-99% coverage
  - Completed: 2026-05-28 | Quality: 97/100

- [x] **COVERAGE-TIER2:** Add tests for important modules (251 stmts)
  - ✅ Modules: config_loader (69), atomic_queue_ops (63), rollback_manager (56), directory_setup (63)
  - ✅ Target: All modules ≥80% coverage — ACHIEVED (94-100%)
  - ✅ Effort: 28:58 | Status: COMPLETE
  - ✅ 128 tests passing, 6/6 modules improved +48pp avg
  - Completed: 2026-05-28 | Quality: 97/100

- [x] **COVERAGE-TIER3:** Add tests for optional modules (522 stmts)
  - ✅ Modules: protocol_audit, healer_metrics_analyzer, tier3_coverage extras
  - ✅ Target: All modules ≥80% coverage — ACHIEVED (100%)
  - ✅ Effort: 9:39 (bonus) | Status: COMPLETE
  - ✅ 73 tests passing, 4/4 modules at 100% coverage
  - Completed: 2026-05-28 | Quality: 97/100

### Cost & Usage Management (🎉 COMPLETED — 4 days early!)

- [x] **COST-001:** Implement cost budgeting & enforcement skill
  - ✅ Per-session, per-hour, per-day, per-week, per-month cost caps
  - ✅ Track actual spend vs. budget + alert at 50%, 75%, 90%, 100%
  - ✅ Graceful degradation: warn before blocking, then block at hard limits
  - ✅ Support provider-agnostic cost models
  - ✅ Effort: 10:23 | Status: MERGED (PR #19)
  - ✅ 99 tests, 93% coverage | Quality: 97/100
  - ✅ Fixed: Thread-safe saves (tempfile + atomic replace), concurrent RMW locking

- [x] **COST-002:** Multi-provider cost aggregation & reporting
  - ✅ Aggregate spend across Claude, GPT, Gemini, GitHub Copilot, OpenCode
  - ✅ Per-provider cost breakdown, efficiency metrics
  - ✅ Weekly/monthly spend reports with trend analysis
  - ✅ Effort: 14:20 | Status: MERGED (PR #19)
  - ✅ 113 tests, 94% coverage, <10ms performance | Quality: 97/100

- [x] **COST-003:** Model selection optimization across providers
  - ✅ Detect which provider offers best cost/quality for given task
  - ✅ Route to cheaper provider when quality delta is acceptable
  - ✅ Track provider-specific model performance
  - ✅ Effort: 53:17 | Status: MERGED (PR #20, v0.37.0 released)
  - ✅ 123 tests, 89% coverage | Quality: 97/100

**Summary:** All cost management work delivered **4 DAYS EARLY** (May 28 vs June 1 deadline)
- 3 skills implemented, tested, merged to main
- 335 total tests across COST-001/002/003
- 633 tests added across TIER1/2/3 coverage
- 0 regressions across 3,988 total tests
- v0.38.0 tagged and released

---

---

## ✅ COMPLETED

### Phase 1.5: Security Hardening (Completed 2026-05-30)

- [x] **PHASE-1.5-FIX-1:** Queue Path Enforcement (Runtime + Git Hook)
  - ✅ Implemented `src/skills/_meta/queue-path-validator/`
  - ✅ Canonical path: `~/.agentic-engineers/{session-id}/{harness}/queue/`
  - ✅ Runtime validator rejects queue injection/poisoning attempts
  - ✅ Git hook enforces canonical paths in all DELEGATE/HANDBACK files
  - ✅ 5+ tests passing, no CI failures
  - ✅ Quality: 95/100

- [x] **PHASE-1.5-FIX-2:** Audit Trail via spec_version Field
  - ✅ Added `spec_version` field to DELEGATE and HANDBACK schemas
  - ✅ Format validation: `\d+\.\d+(-.+)?` (e.g., "1.0", "1.1-2026-05-28")
  - ✅ HANDBACK spec_version must match DELEGATE (audit trail linkage)
  - ✅ SPAN records include spec_version for audit queries
  - ✅ 5+ tests passing
  - ✅ Quality: 94/100

- [x] **PHASE-1.5-FIX-3:** Agent Definition Verification (Tri-Level)
  - ✅ Generated `.agents_verification_sha` from AGENTS.md
  - ✅ Added `model_verification_sha` field to DELEGATE schema
  - ✅ Git hook validates agent definitions match current state
  - ✅ Runtime check in Orchestrator prevents model downgrade attacks
  - ✅ 5+ tests passing
  - ✅ Quality: 96/100

- [x] **PHASE-1.5-FIX-4:** Security-Critical DELEGATE Fields
  - ✅ Added `security_scope` enum (auth, crypto, pii, secrets, injection, supply_chain)
  - ✅ Added `approval_gate` field (lead_engineer, principal_engineer, security_engineer, cto)
  - ✅ Added `audit_required` boolean flag
  - ✅ Routing rules: security tasks routed to Security Engineer minimum
  - ✅ Pre-push hook validation: security_scope requires approval_gate and audit_required
  - ✅ 10+ tests passing
  - ✅ Quality: 97/100

- [x] **PHASE-1.5-FIX-5:** Orchestrator Enforcement Decorator
  - ✅ Created `@enforce_delegate_requirement` decorator in `src/orchestration/decorators.py`
  - ✅ Applied to all Orchestrator.invoke() and Orchestrator.delegate() methods
  - ✅ Validates: DELEGATE schema, required fields, queue paths, spec_version, model_verification_sha, security routing, approval gates
  - ✅ Error handling: explicit EnforcementError with fix suggestions, never silent failures
  - ✅ Audit trail logging for all validation failures
  - ✅ 8+ tests passing
  - ✅ Quality: 96/100

**Phase 1.5 Summary:**
- ✅ All 5 critical fixes implemented and tested
- ✅ 33+ unit tests + 5+ integration tests passing
- ✅ 95%+ coverage on new code
- ✅ Zero regressions across test suite
- ✅ Ready for Phase 1 (spec audit) to proceed
- ✅ Framework now self-enforces security hardening

---

## 📅 CONSOLIDATION ROADMAP

**Objective:** Simplify, stabilize, and polish the agentic-engineers framework. Focus on harness compatibility, skills audit, and production-readiness.

### Milestone 1 (CURRENT): Phase 1.5 Security Hardening ✅ COMPLETE
**Target Date:** 2026-05-30 | **Status:** ✅ DELIVERED  
**Deliverables:**
- ✅ Queue path enforcement (runtime + git hook validation)
- ✅ Audit trail via spec_version field
- ✅ Agent definition verification (tri-level)
- ✅ Security-critical DELEGATE fields (security_scope, approval_gate, audit_required)
- ✅ Orchestrator enforcement decorator with error handling

**Quality Metrics:**
- 38+ tests passing | 95%+ coverage | Zero regressions
- Quality Score: 96/100 | Confidence: 97%

---

### Milestone 2 (NEXT): Harness Stability Across All Platforms
**Target Timeline:** 2-3 weeks (2026-06-13)  
**Priority:** CRITICAL  
**Objective:** Ensure OpenCode, Claude Code, and Copilot CLI harnesses achieve ≥95% compatibility and reliability.

#### OpenCode Harness
- [ ] **OPENCODE-QUEUE-PATH-DETECTION:** Implement harness detection for canonical queue paths
  - Detect session-id and harness type from context
  - Enable proper routing of work through OpenCode harness
  - Blocks: Framework users cannot properly route tasks
  - Effort: 2-3 hours | Owner: Engineer

- [ ] **OPENCODE-HARNESS-CHECKER:** Validate harness configuration at runtime
  - Startup checks: agents loaded, skills available, queue paths valid
  - Effort: 1-2 hours | Owner: Quality Engineer

- [ ] **OPENCODE-RUNNER-INTEGRATION:** Full runner lifecycle integration
  - Task queueing, execution, result retrieval
  - Effort: 2-3 hours | Owner: Senior Engineer

#### Claude Code Harness
- [ ] **CLAUDE-AGENT-AVAILABILITY:** Ensure all 8 agents render and load
  - Verify agent definitions, role assignments, model routing
  - Effort: 2-3 hours | Owner: Quality Engineer

- [ ] **CLAUDE-SKILL-RENDERING:** Full skill catalog rendering and accessibility
  - Test all 14 skills accessible within Claude Code environment
  - Effort: 2-3 hours | Owner: Quality Engineer

#### Copilot CLI Harness
- [ ] **COPILOT-MODEL-ROUTING:** Implement intelligent model selection
  - Route tasks to appropriate model (Haiku/Sonnet/Opus) based on complexity
  - Effort: 2-3 hours | Owner: Model Engineer

- [ ] **COPILOT-TOKEN-TRACKING:** Full token usage and cost visibility
  - Track per-task costs, cumulative session spend, budget alerts
  - Effort: 2-3 hours | Owner: Model Engineer

**Success Metrics:**
- All harnesses pass 100+ compatibility tests
- ≥95% success rate on standard delegation workflows
- Zero silent failures or compatibility regressions
- Full end-to-end telemetry enabled

---

### Milestone 3 (ONGOING): Skills Audit & Consolidation
**Target Timeline:** Ongoing (continuous)  
**Priority:** HIGH  
**Objective:** Stabilize skill ecosystem, improve quality and maintainability.

#### Skills Inventory & Audit
- [ ] **SKILLS-AUDIT:** Review all 14 skills
  - Assess: value, usage, maintenance burden, test coverage
  - Categorize: core (essential), utility (helpful), experimental (proof-of-concept)
  - Effort: 2-3 hours | Owner: Lead Engineer

#### Skills Standardization
- [ ] **SKILLS-STANDARDIZATION:** Enforce consistent standards
  - SKILL.md format alignment (all 14 skills)
  - Test coverage: ≥85% per skill
  - Documentation completeness
  - Effort: 3-5 hours | Owner: Quality Engineer

#### Deprecated Skills
- [ ] Review and archive low-value or experimental skills
  - Move to `docs/archive/deprecated-skills/` with restoration instructions
  - Effort: 1-2 hours | Owner: Senior Engineer

---

## 🎯 Feature Freeze & Post-Freeze Policy

**Feature Freeze Date:** 2026-06-15 (Post-Milestone 3)

### What Happens at Freeze:
No new skills or agents may be added to the framework after this date. All API additions, new agent roles, and skill implementations freeze.

### Post-Freeze Work Only (June 15 onwards):
- ✅ Bug fixes (reported issues, regressions, security)
- ✅ Performance improvements (optimization, latency reduction)
- ✅ Documentation (guides, examples, standards)
- ✅ Polish (UX, error messages, consistency)
- ✅ Dependency updates (security patches, compatibility)

### What's NOT Allowed Post-Freeze:
- ❌ New skills or agents
- ❌ New API endpoints or DELEGATE fields
- ❌ Major refactoring or architectural changes
- ❌ Feature additions or scope creep

**Rationale:** Consolidation phase focuses on stability, reliability, and polish—not feature velocity. Framework is feature-complete for production.

---

## 📋 POST-MERGE ROADMAP

### OpenCode Integration Fixes (Priority: HIGH)
- [ ] **OPENCODE-QUEUE-PATH-DETECTION:** Implement harness detection for canonical queue paths
  - Current: OpenCode uses generic queue path detection
  - Fix: Detect session-id and harness type from context
  - Blocks: Framework users cannot properly route work through OpenCode harness
  - Effort: 2-3 hours | Owner: Engineer
  - Link: See PHASE-1.5-ORCHESTRATION-PLAN.md

- [ ] **OPENCODE-HARNESS-CHECKER:** Validate harness configuration at runtime
  - Current: No validation that OpenCode harness is properly configured
  - Fix: Add startup checks: agents loaded, skills available, queue paths valid
  - Effort: 1-2 hours | Owner: Quality Engineer

### Harness Compatibility & Evaluation Testing (Priority: CRITICAL)
**Problem:** Recent harness/model updates are causing silent compatibility flaps and feature regressions. Need end-to-end feedback loop testing.

- [ ] **EVALS-001: Harness Integration Tests**
   - Build comprehensive test suite for copilot|opencode|claude CLI harnesses
   - Test standard prompts/delegations/skills across all harnesses
   - Capture success/fail results with pass/fail thresholds
   - Report compatibility matrix: (harness × model × feature)
   - Effort: 2-3 weeks | Priority: CRITICAL | Owner: Quality Engineer
   - Success Metric: All harnesses pass standard eval suite with ≥95% success rate

- [ ] **EVALS-002: Model Compatibility Matrix**
   - Build test suite calling each model (haiku, sonnet, opus) with standard DELEGATE blocks
   - Measure response quality, latency, cost
   - Detect model regressions early (breaking changes after model updates)
   - Effort: 1-2 weeks | Priority: HIGH | Owner: Model Engineer

- [ ] **EVALS-003: Skill Interoperability Tests**
   - Test each skill against all harnesses (copilot, opencode, claude, pi)
   - Validate skill outputs meet HANDBACK schema requirements
   - Report skill-by-harness compatibility
   - Effort: 1-2 weeks | Priority: HIGH | Owner: Quality Engineer

- [ ] **EVALS-004: End-to-End Delegation Workflows**
   - Create standard delegation scenarios (simple task, escalation, parallel work)
   - Run through full workflow on each harness/model combo
   - Measure success rate, latency, cost
   - Report pass/fail + threshold analysis
   - Effort: 2-3 weeks | Priority: HIGH | Owner: Senior Engineer

- [ ] **EVALS-005: Continuous Evaluation Pipeline (CI/CD Integration)**
   - Add nightly evaluation job to GitHub Actions
   - Run standard eval suite against all harnesses + models
   - Generate compatibility report automatically
   - Alert on regressions (model incompatibility, harness drift)
   - Effort: 1-2 weeks | Priority: MEDIUM | Owner: Principal Engineer

- [ ] **EVALS-INFRASTRUCTURE: Evaluation Framework**
   - Create reusable `src/skills/_meta/evaluation-framework/` skill
   - Standardized test case format, result reporting, threshold checking
   - Integration with CI/CD, human-readable reports
   - Effort: 2 weeks | Priority: CRITICAL | Owner: Senior Engineer
   - Deliverable: Pluggable framework for adding new evaluation scenarios

### Documentation Polish & Consolidation (Priority: MEDIUM)
- [ ] **README-POLISH:** Update top section with Phase 1.5 completion and consolidation vision
   - Add "Phase: Simplify, Reduce, and Polish" banner after intro
   - Add Evaluation & Compatibility Testing section
   - Link to evaluation roadmap
  - Explain: We are in consolidation phase, not feature-add
  - Link to TODO.md for detailed roadmap
  - Effort: 1 hour | Owner: Orchestrator

- [ ] **CONSOLIDATION-ROADMAP:** Add structured roadmap to TODO.md
  - Timeline: "Stable across copilot|opencode|claude CLI, then polish-only"
  - Focus areas: skills audit, agent role clarification, enforcement consistency
  - Feature freeze date: TBD (after harness stability achieved)
  - Effort: 1 hour | Owner: Orchestrator

### Feature Freeze & Polish Timeline
- **Milestone 1 (Current):** Phase 1.5 security hardening (COMPLETE ✅)
- **Milestone 2 (Next):** Harness stability across all platforms (2-3 weeks)
  - OpenCode harness: queue path detection, runner integration
  - Claude Code harness: agent availability, skill rendering
  - Copilot CLI harness: model routing, token tracking
- **Milestone 3:** Skills audit and consolidation (ongoing)
  - Review: 14 skills, prioritize high-value, deprecate low-value
  - Standardize: SKILL.md format, test coverage, documentation
- **Feature Freeze:** Post-milestone 3 (target: June 15, 2026)
  - No new skills or agents after freeze date
  - Focus: bug fixes, performance, documentation, polish

---

## 🔵 PLANNED (Phase J+)

- [ ] **STANDARDS-002:** Create STANDARDS.md comprehensive guide
   - Full standards alignment, compliance matrix, roadmap
   - Effort: 4-6 hours | Owner: Senior Engineer

### Framework Integration (Opt-In Required)
> **Status:** ⏸️ PAUSED — Research complete. No work starts until explicitly approved.  
> **Research:** [docs/FRAMEWORKS/](docs/FRAMEWORKS/)

- [ ] **FRAMEWORK-001:** Anthropic SDK integration verification
- [ ] **FRAMEWORK-002:** OpenAI SDK integration
- [ ] **FRAMEWORK-003:** Ollama local LLM runtime
- [ ] **FRAMEWORK-004:** CrewAI orchestration layer documentation
- [ ] **FRAMEWORK-005:** Pydantic AI type-safe agents

### Cost & Usage Management (🚨 HIGH PRIORITY — June 1 deadline)
> **Context:** As of June 1, 2026 (8 days from NOW), all LLM providers charge per usage token + time, not flat subscription. Framework users need cost controls, visibility, and multi-provider optimization. April 2026 usage equivalent to $550 USD in AI credits (GitHub Copilot subsidy was ~$39 AUD/month equivalent).

- [ ] **COST-001:** Implement cost budgeting & enforcement skill
  - Per-session, per-hour, per-day, per-week, per-month cost caps (configurable in credits/$)
  - Track actual spend vs. budget + alert at 50%, 75%, 90%, 100%
  - Graceful degradation: warn before blocking, then block at hard limits
  - Support provider-agnostic cost models (different rates per provider)
  - Effort: 3-4 days | Owner: Senior Engineer + Model Engineer
  - **Critical:** Must be ready by June 1

- [ ] **COST-002:** Multi-provider cost aggregation & reporting
  - Aggregate spend across Claude (Anthropic), GPT (OpenAI), Gemini (Google), GitHub Copilot, OpenCode
  - Per-provider cost breakdown, efficiency metrics (cost per task, cost per test, etc.)
  - Weekly/monthly spend reports with trend analysis
  - Effort: 2-3 days | Owner: Metrics + Model Engineer
  - **Critical:** Must be ready by June 1

- [ ] **COST-003:** Model selection optimization across providers
  - Detect which provider offers best cost/quality for given task
  - Route to cheaper provider when quality delta is acceptable
  - Track provider-specific model performance (Haiku vs Claude-3.5-Sonnet vs GPT-4 mini, etc.)
  - Effort: 2-3 days | Owner: Model Engineer
  - **Critical:** Must be ready by June 1

- [~] **COST-004:** Local model support (Ollama, llama.cpp, Apple MLX, NVidia)
  - [x] **Phase 1 (Planning):** Define harness architecture for local LLMs
    - [x] How agents connect to local Ollama instance (`/api/tags`, injectable client)
    - [x] Fallback logic when local unavailable (route to cloud)
    - [x] Cost accounting (local = $0 but slower)
    - [x] Model availability detection + auto-selection
  - [x] **Phase 2 (Minimal impl):** Ollama integration (most popular local runtime)
    - [x] Detect Ollama instance (localhost:11434 or env var)
    - [x] List available models, select best-fit by size/quality
    - [x] Route Haiku-class tasks to local, Sonnet/Opus to cloud when local insufficient
    - [x] Fallback: if local model not available, use cloud
    - ✅ Skill: `src/skills/local-model-runtime/` — 30 tests, 95% coverage
    - ✅ Stdlib-only (urllib); reads zero-cost catalogue from `providers.yaml`
  - [ ] **Phase 3 (Future):** llama.cpp, Apple MLX, NVidia CUDA support
  - Effort: Phase 1: 1-2 days (planning) | Phase 2: 3-5 days (impl) | Phase 3: TBD
  - Owner: Principal/Senior Engineer
  - **Strategic:** Local models → 95% cost reduction long-term, essential for users running on local hardware

### Future Features
- [ ] **COMPARISON-002:** Update orchestration framework comparisons to include Gas City
  - Gas City v1.0.0 released late April 2026 (refinement of Gastown by Steve Yegge)
  - Add to README.md Quick Comparison Table and detailed analysis
  - Effort: 2-3 hours | Owner: Engineer
- [x] **MONITORING-001:** Automated document quality monitoring
  - Continuous link validation, staleness detection (30+ days)
  - ✅ Done: `src/skills/doc-quality-monitor` — broken-link, missing-section,
    staleness, placeholder-leakage & structure checks; JSON + Markdown report
    with configurable health-score gate. 37 tests passing (TDD). CLI + library API.
- [ ] **ORCHESTRATOR-001:** Continuous compliance validation
  - Monthly full standards audit, automated alerts on drift
- [ ] **SKILL-REPO-INIT-001:** Implement repo-init skill for new repository onboarding
  - Effort: 3-5 days | Owner: Senior/Principal Engineer

---

## 📊 Phase Status

| Phase | Status | Completion |
|-------|--------|------------|
| 1–6: Core Framework | ✅ Complete | 100% |
| Phase 3: Token Visibility | ✅ Complete | 100% |
| Phase B–E: Skills & Harness | ✅ Complete | 100% |
| Phase G: Documentation Refresh | ✅ Complete | 100% |
| Doc Consolidation Round 2 | ✅ Complete | 100% |
| Skills: todo-maintenance | ✅ Complete | 100% (92/100 quality) |
| Skills: doc-quality | ✅ Complete | 100% (94/100 quality) |
| Market: Gastown Comparison | ✅ Complete | 100% (94/100 quality) |
| README: Key Benefits & Discoveries | ✅ Complete | 100% (94/100 quality) |
| README: Simplified Example Section | ✅ Complete | 100% (95/100 quality) |
| Phase H: Test Coverage | ✅ Complete | 100% (633 tests TIER1/2/3) |
| Phase H-TIER1: Critical Modules | ✅ Complete | 100% (432 tests) |
| Phase H-TIER2: Important Modules | ✅ Complete | 100% (128 tests) |
| Phase H-TIER3: Optional Modules | ✅ Complete | 100% (73 tests) |
| Cost & Usage Management (COST-001/002/003) | ✅ Complete | 100% (335 tests, v0.38.0 released) |
| Phase 1.5: Security Hardening (5 FIXes) | ✅ Complete | 100% (38+ tests, all security gates passed) |
| Phase I: Standards Compliance | 🔴 Blocked | 0% (OVERDUE 8 days) |
| Framework Integration | ⏸️ Paused | Research only |

---

## 📋 Implementation Rules

✅ **TDD-First:** All code changes follow Red-Green-Refactor  
✅ **Quality Gates:** Minimum 85% coverage per changed module  
✅ **SPEC.md Protection:** All changes routed through spec-management skill  
✅ **Queue Protocol:** All delegations go through `artifacts/queue/`  
✅ **Zero Regressions:** All tests passing before commit  
✅ **Documentation:** All changes documented, links updated  

---

**Owner:** Orchestrator Agent  
**Next Review:** 2026-05-24 (weekly)
