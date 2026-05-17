# TODO: agentic-engineers

**Last Updated:** 2026-05-17  
**Status:** Active — Phase G (Documentation Refresh) in progress

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

## 🔴 IN PROGRESS

### Phase G: Documentation Refresh (This Sprint)

- [x] **DOC-AUDIT-001:** Create `docs/DOCUMENTATION-AUDIT.md`
- [x] **DOC-README-001:** Rewrite README.md (<500 lines, accurate, current)
- [x] **DOC-TODO-001:** Refresh TODO.md with current May 2026 status
- [ ] **DOC-SPEC-001:** Update SPEC.md with Phase 3 token visibility requirements
- [ ] **DOC-QS-001:** Create `docs/QUICK-START-TOKEN-VISIBILITY.md`
- [ ] **DOC-QS-002:** Create `docs/QUICK-START-BUDGET-CHECKING.md`
- [ ] **DOC-QS-003:** Create `docs/QUICK-START-PRODUCTION-DEPLOYMENT.md`
- [ ] **DOC-INDEX-001:** Create `docs/INDEX.md` (master documentation index)
- [ ] **DOC-ARCHIVE-001:** Move root-level `*_IMPLEMENTATION.md` files to `docs/archive/phase-reports/`

---

## 🟡 NEXT UP (Phase H)

### Test Coverage Improvements
- [ ] **COVERAGE-001:** Add test files for 0% coverage modules
  - Modules: artifact_manager, delegate_validator, gray_zone_reviewer, metrics_writer, spec_validator, workflow, lead_review_cli
  - Target: 85%+ coverage per module
  - Effort: 1 week | Owner: Quality Engineer

- [ ] **TDD-001:** Fix remaining failing tests per TDD-ROADMAP.md
  - Priority order in `docs/TDD-ROADMAP.md` P0 section
  - Effort: 3-4 days | Owner: Lead Engineer + Engineer

### Skills Implementation
- [ ] **SKILL-TODO-001:** Implement todo-maintenance skill
  - Auto-sync queue DELEGATEs ↔ TODO.md on HANDBACK received
  - Effort: 1-2 days | Owner: Engineer

- [ ] **SKILL-DOC-QUALITY-001:** Implement doc-quality skill
  - Link validation, cross-ref checks, staleness flagging
  - Constraint: Exclude SPEC.md from all checks
  - Effort: 2-3 days | Owner: Quality Engineer

### Documentation Cleanup
- [ ] **CLEANUP-001:** Archive PHASE-3/4 planning docs
  - Move ~12 files to `docs/archive/phase-planning/`
  - Effort: 1-2 hours | Owner: Engineer

- [ ] **CLEANUP-002:** Reduce tracked files to <150
  - Current: ~240 → Target: <150
  - Effort: 1 day | Owner: Senior Engineer

---

## 🔵 PLANNED (Phase I+)

### Standards Compliance
- [ ] **STANDARDS-001:** Update SPEC.md with external standards section
  - Add: AGENTS.md, Claude Code, GitHub Copilot, agentskills.io
  - Authority: spec-management skill (Principal/Lead approval)
  - Effort: 1 day | Owner: Principal Engineer

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
| Phase G: Documentation Refresh | 🔄 In Progress | ~40% |
| Phase H: Test Coverage | ⏳ Planned | 0% |
| Phase I: Standards Compliance | ⏳ Planned | 0% |
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
