# TODO: agentic-engineers Implementation Roadmap

**Last Updated:** May 9, 2025  
**Status:** Active execution phase (TDD-first approach)

---

## 🔴 PRIORITY (Must Do First)

### Foundation Fixes (Phase 1: Weeks 1-2)

- [ ] **TDD-001:** Write RED-phase tests for 15 failing test fixes
  - Reference: `docs/TDD-ROADMAP.md` (P0 section)
  - Tests must follow `test_<action>_<scenario>_<expected>` format
  - Each test in `test(wip):` commit before code
  - Effort: 1 day
  - Owner: Lead Engineer

- [ ] **AGENTS-001:** Write tests for AGENTS.md location validation
  - Test: `tests/test_agents_md_location.py` (RED first)
  - Verify canonical is `docs/AGENTS.md`
  - Detect if `src/docs/AGENTS.md` exists
  - Effort: 2-3 hours
  - Owner: Engineer

- [ ] **AGENTS-002:** Delete stale `src/docs/AGENTS.md`
  - After AGENTS-001 tests pass
  - Preserve git history (git rm)
  - Update any cross-references
  - Effort: 1 hour
  - Owner: Engineer

- [ ] **TDD-002:** Fix 15 failing tests per TDD-ROADMAP.md
  - Priority order in TDD-ROADMAP.md P0 section
  - Minimum 85% coverage per changed module
  - All tests pass, zero regressions
  - Effort: 3-4 days
  - Owner: Lead Engineer + Engineer team

- [ ] **COVERAGE-001:** Add test files for 0% coverage modules
  - Modules: artifact_manager, delegate_validator, gray_zone_reviewer, implementations, metrics_writer, spec_validator, workflow, lead_review_cli
  - Reference: `docs/TESTS-NEEDED.md`
  - Target: 85%+ coverage per module
  - Effort: 1 week
  - Owner: Quality Engineer

- [ ] **SKILL-SPEC-MGT-001:** Implement spec-management skill
  - Purpose: Exclusive SPEC.md changes with audit trail
  - Authority: Principal Engineer + Security Engineer only
  - Features: Change proposal, impact analysis, approval routing, changelog
  - Reference: `docs/SKILL-SPECS.md` (Skill 3)
  - Model: Opus (highest capability)
  - Effort: 2-3 days
  - Owner: Principal Engineer

- [ ] **SKILL-SPEC-VAL-001:** Implement spec-validator skill
  - Purpose: Enforce SPEC.md compliance in implementation
  - Features: Diff analysis, compliance checking, enforcement
  - Can detect: removed features, architecture drift, undocumented changes
  - Model: Sonnet
  - Effort: 2-3 days
  - Owner: Senior Engineer

- [ ] **SKILL-AGENT-CREATOR-001:** Implement agent-creator skill
  - Purpose: Create new agents compliant with agentic-engineers spec
  - Features: Template generation, spec compliance checks, integration verification
  - Auto-includes: DELEGATE/HANDBACK protocol, TDD tests, SKILL.md frontmatter
  - Model: Sonnet
  - Effort: 2-3 days
  - Owner: Senior Engineer

---

## 🟡 STANDARD (Should Do Next)

### Standards Documentation (Phase 2: 2-3 days)

- [ ] **STANDARDS-001:** Update SPEC.md with standards section
  - Add: AGENTS.md, Claude Code, GitHub Copilot, agentskills.io
  - Format: Reference subsection with links + compliance status
  - Reference: `docs/STANDARDS-DOCUMENTATION-PLAN.md`
  - Authority: spec-management skill (Principal/Lead approval)
  - Effort: 1 day
  - Owner: Principal Engineer

- [ ] **STANDARDS-002:** Update README.md with standards compliance
  - Add: Standards Compliance section with link to STANDARDS.md
  - Format: Brief summary + link to detailed guide
  - Effort: 2-3 hours
  - Owner: Senior Engineer

- [ ] **STANDARDS-003:** Create STANDARDS.md comprehensive guide
  - Reference: `docs/STANDARDS-DOCUMENTATION-PLAN.md`
  - Content: Full standards alignment, compliance matrix, roadmap
  - Structure: Navigation guide + status + next steps
  - Effort: 4-6 hours
  - Owner: Senior Engineer

### Skills Implementation (Phase 2-3: 1-2 weeks)

- [ ] **SKILL-QUEUE-MGT-001:** Implement queue-management skill
  - Purpose: Automate adding tasks to both queue/ and TODO.md simultaneously
  - Trigger: User command "add to queue: <task spec>" or programmatic calls
  - Features:
    - Parse task specifications (structured input)
    - Validate QUEUE-PROTOCOL format (task_id, role, model, effort, scope, plan, criteria)
    - Generate DELEGATE JSON file in ~/.copilot/queue/incoming/
    - Add entry to repo TODO.md in appropriate section (PRIORITY/STANDARD/OPTIONAL)
    - Commit both changes with structured message
    - Validate format and no duplicates
  - Owner: Engineer (or could be internal Orchestrator skill)
  - Model: Haiku
  - Effort: 1-2 days
  - Success Criteria:
    - Can add tasks via CLI: "add-to-queue --task-id X --role Y --scope Z..."
    - Can add tasks via JSON: reads task spec file, auto-generates both files
    - TODO.md entry includes: task_id, description, effort, owner, reference docs
    - DELEGATE file includes: full spec with plan, success criteria, constraints
    - Both committed atomically in single git commit
    - Prevents duplicate task_ids across queue + TODO.md

- [ ] **SKILL-TODO-001:** Implement todo-maintenance skill
  - Purpose: Auto-sync queue DELEGATEs ↔ TODO.md
  - Trigger: On HANDBACK received from queue
  - Features: Auto-update status, priority sync, completion tracking
  - Reference: `docs/SKILL-SPECS.md` (Skill 1)
  - Model: Haiku
  - Effort: 1-2 days
  - Owner: Engineer

- [ ] **SKILL-DOC-QUALITY-001:** Implement doc-quality skill
  - Purpose: Link validation, cross-ref checks, staleness flagging
  - Trigger: During quality gates + manual on-demand
  - Features: Link validation, formatting checks, consistency verify
  - CONSTRAINT: Explicitly exclude SPEC.md from all checks
  - Reference: `docs/SKILL-SPECS.md` (Skill 2)
  - Model: Sonnet
  - Effort: 2-3 days
  - Owner: Quality Engineer

### Documentation Consolidation (Phase 3: 1-2 weeks)

- [ ] **CLEANUP-001:** Archive PHASE-5/6 docs
  - Move 19 files: PHASE-*.md, related docs
  - Destination: `docs/archive/phase5/`, `docs/archive/phase6/`
  - Preserve git history (git mv)
  - Update cross-references
  - Reference: `docs/CONSOLIDATION-ROADMAP.md` (commits 1-3)
  - Effort: 2-3 hours
  - Owner: Senior Engineer

- [ ] **CLEANUP-002:** Consolidate legacy session documentation
  - Move session notes, old guides to `docs/archive/sessions/`
  - Keep: recent guides, current references
  - Reference: `docs/CONSOLIDATION-ROADMAP.md` (commits 4-6)
  - Effort: 2-3 hours
  - Owner: Senior Engineer

- [ ] **CLEANUP-003:** Clean root directory
  - Remove scattered config files from root
  - Final root: README.md, STANDARDS.md, Makefile, .gitignore, .github/
  - Reference: `docs/CONSOLIDATION-ROADMAP.md` (commits 7-11)
  - Effort: 1-2 hours
  - Owner: Senior Engineer

- [ ] **CLEANUP-004:** Reduce tracked files to <150
  - Current: ~240 → Target: <150
  - Execute CONSOLIDATION-ROADMAP.md sequentially
  - Verify: `git ls-files | wc -l`
  - Effort: 1 week (included in above cleanups)
  - Owner: Senior Engineer

---

## 🟢 OPTIONAL (Nice to Have)

### Standards Roadmap Phases (Q2-Q4 2025)

- [ ] **STANDARDS-PHASE-1:** Claude Code integration
  - Create `/.claude/agents/` with YAML frontmatter
  - Target: 90% Claude Code compliance
  - Timeline: 2-3 days
  - Reference: `docs/STANDARDS-ROADMAP.md` (Phase 1)

- [ ] **STANDARDS-PHASE-2:** MCP server integration
  - Define `.mcp.json`, create MCP server definitions
  - Target: 100% MCP compliance
  - Timeline: 1 week
  - Reference: `docs/STANDARDS-ROADMAP.md` (Phase 2)

- [ ] **STANDARDS-PHASE-3:** CrewAI adapter bridge
  - Build translation layer for CrewAI compatibility
  - Target: 85% CrewAI compliance
  - Timeline: 1 week
  - Reference: `docs/STANDARDS-ROADMAP.md` (Phase 3)

- [ ] **STANDARDS-PHASE-4:** Framework documentation
  - OpenAI Agents SDK, LangChain integration guides
  - Target: 50% OpenAI/LangChain compliance
  - Timeline: 1 week
  - Reference: `docs/STANDARDS-ROADMAP.md` (Phase 4)

---

## 🔵 FUTURE (Research/Design Phase)

- [ ] **SKILL-REPO-INIT-001:** Implement repo-init skill for new repository onboarding
  - Purpose: Initialize new repositories with agentic-engineers framework
  - Triggers: When starting work in a new repo or running /init command
  - Features:
    - Repository analysis (structure, existing config, package managers)
    - SPEC.md generation (establish project specification)
    - Basic housekeeping (gitignore, README structure, docs setup)
    - Framework bootstrap (create agents/, skills/, tests/ structure)
    - Compatibility check (verify model/harness LLM readiness)
    - Efficiency setup (TODO.md, queue structure, initial delegations)
  - Owner: Senior Engineer or Principal Engineer
  - Model: Sonnet (or Opus if architecture decisions needed)
  - Effort: medium-high (estimated 3-5 days for design + implementation)
  - Reference: Will use agent-creator skill + SPEC.md standards
  - Success Criteria:
    - New repo immediately ready for agentic-engineers workflow
    - SPEC.md auto-generated with sensible defaults
    - Directory structure optimized for LLM processing
    - First delegations can be queued immediately
    - Documentation complete for repo-specific standards

- [ ] **MONITORING-001:** Automated document quality monitoring
  - Continuous link validation
  - Staleness detection (flag docs not updated in 30+ days)
  - Coverage metrics dashboard

- [ ] **ORCHESTRATOR-001:** Continuous compliance validation
  - Monthly full standards audit
  - Automated alerts on drift
  - Compliance scorecard dashboard

- [ ] **AGENT-REGISTRY:** Maintain agent registry
  - Track all active agents (8 roles)
  - Version compatibility matrix
  - Feature capability matrix

---

## 📊 Status Tracking

### Phase 1 Progress (Foundation Fixes)
- [ ] TDD foundations complete
- [ ] Failing tests fixed
- [ ] Coverage at 85%+
- [ ] Spec-management skill live
- [ ] Spec-validator skill live
- [ ] Agent-creator skill live

**Target Completion:** May 23, 2025  
**Current Progress:** 0% (starting)

### Phase 2 Progress (Standards & Skills)
- [ ] Standards docs updated
- [ ] todo-maintenance skill live
- [ ] doc-quality skill live
- [ ] Documentation consolidated

**Target Completion:** June 6, 2025  
**Current Progress:** 0% (blocked on Phase 1)

### Phase 3 Progress (Cleanup & Reduction)
- [ ] Tracked files < 150
- [ ] Root directory clean
- [ ] All archives in place

**Target Completion:** June 13, 2025  
**Current Progress:** 0% (blocked on Phase 1-2)

### Phase 4 Progress (Standards Roadmap)
- [ ] Claude Code Phase 1 (June 13)
- [ ] MCP Phase 2 (July 18)
- [ ] CrewAI Phase 3 (August 25)
- [ ] Frameworks Phase 4 (September 29)
- [ ] Monthly validation (October+)

**Target Completion:** October 31, 2025  
**Current Progress:** 0% (blocked on earlier phases)

---

## 🎯 Key Dependencies

- **Phase 1 → Phase 2:** Phase 1 must be 100% complete before Phase 2 starts
- **Phase 2 → Phase 3:** Phase 2 must be 100% complete before Phase 3 starts
- **Phases 3/4:** Can run in parallel with Phase 2 (optional/roadmap items)

---

## 📋 Implementation Rules (Enforced)

✅ **TDD-First:** All code changes must follow Red-Green-Refactor  
✅ **Quality Gates:** Minimum 85% coverage per changed module  
✅ **SPEC.md Protection:** All changes routed through spec-management skill  
✅ **Queue Protocol:** All delegations go through ~/.copilot/queue/  
✅ **Zero Regressions:** All tests passing before commit  
✅ **Documentation:** All changes documented, links updated  

---

**Last Updated:** May 9, 2025 (22:34 UTC - repo-init skill added)  
**Next Review:** 2025-05-16 (weekly)  
**Owner:** Orchestrator Agent
