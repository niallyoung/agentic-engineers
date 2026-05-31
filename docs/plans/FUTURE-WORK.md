# Future Work — agentic-engineers Roadmap

**Last Updated:** 2026-05-31  
**Feature Freeze Target:** 2026-06-15  
**Current Phase:** Consolidation (Harness Stability & Skills Audit)

---

## ✅ Completed Phases

- **Phase 1–6:** Core framework (queue protocol, 8 agents, 3-layer quality gates)
- **Phase A–E:** Skills implementation, harness rendering, token visibility
- **Phase G:** Documentation refresh (README, SPEC.md, TODO.md)
- **Phase H:** Extended test suite (633 tests, 100% passing)
- **Phase 1.5:** Security hardening (5 critical fixes, 38+ tests)

---

## 📅 Active Roadmap

### Milestone 2 (CURRENT): Harness Stability & Compatibility
**Target:** 2026-06-13 | **Effort:** 15–20 hours | **Priority:** CRITICAL

#### OpenCode Harness
- **OPENCODE-QUEUE-PATH-DETECTION** (2–3 hrs)
  - Detect session-id and harness type from context
  - Enable proper task routing through OpenCode
  - Location: `src/harness/opencode/`
  
- **OPENCODE-HARNESS-CHECKER** (1–2 hrs)
  - Startup validation: agents loaded, skills available, queue paths valid
  - Location: `src/harness/opencode/health_check.py`
  
- **OPENCODE-RUNNER-INTEGRATION** (2–3 hrs)
  - Full task queueing, execution, result retrieval lifecycle
  - Location: `src/harness/opencode/runner.py`

#### Claude Code Harness
- **CLAUDE-AGENT-AVAILABILITY** (2–3 hrs)
  - Verify all 8 agents render and load correctly
  - Test role assignments and model routing
  - Location: `src/harness/claude-code/agents/`
  
- **CLAUDE-SKILL-RENDERING** (2–3 hrs)
  - Ensure all 14 skills are accessible in Claude Code environment
  - Location: `src/harness/claude-code/skills/`

#### Copilot CLI Harness
- **COPILOT-MODEL-ROUTING** (2–3 hrs)
  - Implement intelligent model selection (Haiku/Sonnet/Opus by complexity)
  - Location: `src/harness/copilot/router.py`
  
- **COPILOT-TOKEN-TRACKING** (2–3 hrs)
  - Per-task cost tracking, session spend visibility, budget alerts
  - Location: `src/harness/copilot/metrics.py`

**Success Criteria:**
- All harnesses pass 100+ compatibility tests
- ≥95% success rate on standard delegation workflows
- Zero silent failures or compatibility regressions
- Full end-to-end telemetry enabled

---

### Milestone 3 (ONGOING): Skills Audit & Consolidation
**Target:** Continuous | **Effort:** 6–10 hours | **Priority:** HIGH

#### Skills Inventory & Audit
- **SKILLS-AUDIT** (2–3 hrs)
  - Review all 14 skills for value, usage, maintenance burden, test coverage
  - Categorize: core (essential), utility (helpful), experimental (proof-of-concept)
  - Location: `src/skills/`

#### Skills Standardization
- **SKILLS-STANDARDIZATION** (3–5 hrs)
  - Enforce consistent SKILL.md format across all 14 skills
  - Achieve ≥85% test coverage per skill
  - Complete documentation for all skills
  - Location: `src/skills/*/SKILL.md`

#### Deprecated Skills Management
- **DEPRECATE-LOW-VALUE-SKILLS** (1–2 hrs)
  - Archive experimental/low-value skills to `docs/archive/deprecated-skills/`
  - Document restoration instructions
  - Location: `docs/archive/deprecated-skills/`

---

## 🎯 Feature Freeze Policy

**Freeze Date:** 2026-06-15 (Post-Milestone 3)

### Allowed Post-Freeze (Jun 15 onwards)
- ✅ Bug fixes (regressions, security issues)
- ✅ Performance improvements (optimization, latency)
- ✅ Documentation (guides, examples, standards)
- ✅ Polish (UX, error messages, consistency)
- ✅ Dependency updates (security patches)

### Prohibited Post-Freeze
- ❌ New skills or agents
- ❌ New DELEGATE fields or API endpoints
- ❌ Major refactoring or architectural changes
- ❌ Feature additions or scope creep

**Rationale:** Consolidation focuses on stability, reliability, and polish—not feature velocity.

---

## 📊 Metrics & Quality Gates

### Pre-Freeze Requirements
- All milestones 1–3 must pass ≥95% quality gate threshold
- Zero regressions in test suite (current: 633 tests, 100%)
- Full test coverage on new code (≥85% minimum)

### Post-Freeze Maintenance
- Monthly security audit (dependency updates, CVE scans)
- Quarterly performance review (token costs, latency)
- Continuous compatibility monitoring (new model releases)

---

## 📝 Documentation TODOs

Related reference:
- [PHASE-1.5-ORCHESTRATION-PLAN.md](PHASE-1.5-ORCHESTRATION-PLAN.md) — Completed security hardening details
- [TODO.md](../../TODO.md) — Primary task tracking (repository root)
- [src/agents/README.md](../../src/agents/README.md) — Agent implementation standards
- [src/skills/SKILLS-INDEX.md](../../src/skills/SKILLS-INDEX.md) — Skill catalog and status

---

## 🔗 Related Plans

- [SESSION-PLANNING-TEMPLATE.md](SESSION-PLANNING-TEMPLATE.md) — Template for session planning
- [TASK-QUEUE-PROTOCOL-INTEGRATION-001-SUMMARY.txt](TASK-QUEUE-PROTOCOL-INTEGRATION-001-SUMMARY.txt) — Protocol integration notes
- [HANDBACK-TASK-QUEUE-PROTOCOL-INTEGRATION-001.json](HANDBACK-TASK-QUEUE-PROTOCOL-INTEGRATION-001.json) — Integration handback example

---

## Questions or Additions?

File issues with `[FUTURE-WORK]` label or update [TODO.md](../../TODO.md) with new items marked `- [ ]`.
