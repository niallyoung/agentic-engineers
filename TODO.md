# TODO: agentic-engineers

**Last Updated:** 2026-05-18  
**Status:** Active — Phase G Complete, Doc Consolidation Round 2 Complete, Phase H Planning Complete

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

## 🔴 IN PROGRESS

### Phase H: Test Coverage Improvements (Delegated 2026-05-18)

- [ ] **COVERAGE-001:** Add test files for 0% coverage modules (14 modules, 1,361 stmts)
  - TIER 1: core_protocol_validator, protocol_audit, healer-metrics-analyzer, queue_manager, test_validators
  - TIER 2: test_rate_limiting, test_queue_ops, testing_harness, AGENT-IMPLEMENTATION-TEMPLATE
  - TIER 3: test_integration, orchestrator_testing_harness, errors, conftest, test_core_protocol_validator
  - Target: 85%+ overall, all modules ≥80%
  - Effort: 32.5 hours | Owner: Quality Engineer
  - Deadline: 2026-05-24
  - Task ID: 2026-05-18-phase-h-test-coverage

### Phase I: Standards Compliance (Delegated 2026-05-18)

- [ ] **STANDARDS-001:** Update SPEC.md with external standards section
  - Add: AGENTS.md, Claude Code, GitHub Copilot, agentskills.io
  - Authority: spec-management skill (Principal/Lead approval)
  - Effort: 1-2 days | Owner: Principal Engineer
  - Deadline: 2026-05-20
  - Task ID: 2026-05-18-phase-i-standards-compliance

- [ ] **STANDARDS-002:** Create STANDARDS.md comprehensive guide
  - Full standards alignment matrix, compliance checklist, implementation roadmap
  - Effort: Included in STANDARDS-001
  - Owner: Principal Engineer

### Skills Implementation (Delegated 2026-05-18)

- [ ] **SKILL-TODO-001:** Implement todo-maintenance skill
  - Auto-sync queue DELEGATEs ↔ TODO.md on HANDBACK received
  - Bidirectional sync, conflict detection, weekly reporting
  - Effort: 1-2 days | Owner: Engineer
  - Deadline: 2026-05-20
  - Task ID: 2026-05-18-skill-todo-maintenance

- [ ] **SKILL-DOC-QUALITY-001:** Implement doc-quality skill
  - Link validation, cross-ref checks, staleness flagging
  - Quality metrics, HTML+Markdown reports, CI/CD integration
  - Constraint: Exclude SPEC.md from all checks
  - Effort: 2-3 days | Owner: Quality Engineer
  - Deadline: 2026-05-22
  - Task ID: 2026-05-18-skill-doc-quality

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

### Future Features
- [ ] **MONITORING-001:** Automated document quality monitoring
  - Continuous link validation, staleness detection (30+ days)
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
| Phase H: Test Coverage | 🔄 Delegated | ~0% (Quality Engineer) |
| Phase I: Standards Compliance | 🔄 Delegated | ~0% (Principal Engineer) |
| Skills: todo-maintenance | 🔄 Delegated | ~0% (Engineer) |
| Skills: doc-quality | 🔄 Delegated | ~0% (Quality Engineer) |
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
