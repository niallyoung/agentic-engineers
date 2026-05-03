# Model Centralization Architecture — Complete Design Index

**Status:** ✅ DESIGN COMPLETE — Ready for Implementation  
**Created:** 2025-05-15  
**Phase:** Ready for Handoff to Engineer  
**Total Documentation:** 2,380 lines across 4 documents

---

## Quick Navigation

### 👨‍💼 For Leadership/Principal Engineer
Start here: **ADR-model-centralization.md** (5 min read)
- Status and approval chain
- Decision summary with rationale
- Consequences and risk mitigation

### 👨‍💻 For Engineer (Execution)
Start here: **model-implementation-roadmap.md** (detailed task plan)
- 7 phases, 20 specific tasks
- Per-task: acceptance criteria, dependencies, estimates
- Timeline: 3-4 weeks
- Then: **architecture-model-centralization.md** for technical details

### 📋 For Team (Context)
Start here: **model-centralization-design-summary.md** (10 min read)
- Current state → Desired state
- Key design decisions
- Effort and timeline
- File changes summary

### 🔍 For Deep Dive
**architecture-model-centralization.md** (full specification)
- Current state analysis
- 5 architecture components
- Integration points
- Technical specifications

---

## Document Overview

### 1. ADR-model-centralization.md (278 lines)
**Purpose:** Executive decision record  
**Audience:** Leadership, Principal Engineer  
**Time to Read:** 5-10 minutes

**Sections:**
- Status: APPROVED
- Context & Problem Statement
- Decision & Architecture
- Alternatives Considered
- Consequences (positive/negative/risks)
- Implementation Reference
- Success Metrics

**When to use:** Understand why this approach was chosen

---

### 2. model-centralization-design-summary.md (449 lines)
**Purpose:** Quick reference guide  
**Audience:** Everyone  
**Time to Read:** 10-15 minutes

**Sections:**
- Deliverables overview
- Key design decisions (5 major decisions)
- Architecture components (5 layers)
- Current state → Desired state
- Role → Model mapping table (13 agents)
- Effort estimation (3-4 weeks)
- Success criteria checklist

**When to use:** Get quick overview, understand big picture

---

### 3. architecture-model-centralization.md (911 lines)
**Purpose:** Complete technical specification  
**Audience:** Engineers, Architects  
**Time to Read:** 30-45 minutes

**Sections:**
- Executive Summary
- Current State Analysis
  - Existing models.yaml
  - Hard-coded references (4 locations)
  - Existing infrastructure
- Architecture Design (5 components)
  1. Centralized Configuration (models.yaml)
  2. Format Conversion Strategy (ModelResolver)
  3. Role → Model Mapping (13 agents)
  4. Environment-Specific Overrides
  5. Fallback & Default Strategies
- Integration Points (agents, rendering, docs, tests)
- Implementation Roadmap (7 phases summary)
- Technical Specifications
  - ModelResolver API
  - JSON Schema
  - Environment Variables
- Implementation Roadmap (7 phases summary)
- Risks and Mitigations
- Success Metrics

**When to use:** Implement the design, understand all details

---

### 4. model-implementation-roadmap.md (742 lines)
**Purpose:** Detailed task execution plan  
**Audience:** Engineer (primary), Project Manager  
**Time to Read:** 20-30 minutes (or skim sections as needed)

**Sections:**
- Overview (effort, timeline, risk)
- Phase 1: Foundation (3 tasks)
  - Task 1.1: ModelResolver class (2h)
  - Task 1.2: Environment overrides (1.5h)
  - Task 1.3: models.yaml validation (1h)
- Phase 2: Agent Frontmatter (2 tasks)
  - Task 2.1: Update 13 agent files (1.5h)
  - Task 2.2: Update render pipeline (2h)
- Phase 3: Copilot CLI (2 tasks)
  - Task 3.1: Provider rendering (2h)
  - Task 3.2: Test consistency (1.5h)
- Phase 4: Documentation (3 tasks)
  - Task 4.1: Doc generator (2h)
  - Task 4.2: Update SPEC.md (1.5h)
  - Task 4.3: Update README.md (1h)
- Phase 5: Testing (3 tasks)
  - Task 5.1: Integration tests (3h)
  - Task 5.2: Validation script (2h)
  - Task 5.3: CI/CD integration (1h)
- Phase 6: Operations (2 tasks)
  - Task 6.1: Management guide (2h)
  - Task 6.2: Update INSTALL.md (1h)
- Phase 7: Cleanup (2 tasks)
  - Task 7.1: Deprecation markers (1h)
  - Task 7.2: Final audit (1h)
- Success Metrics
- References

Each task includes:
- Title & type
- Story points & time estimate
- Acceptance criteria (10-20 per task)
- Implementation notes
- Dependencies & blocking relationships
- Owner & reviewer
- Test cases & validation steps

**When to use:** Execute implementation, track progress

---

## Reading Paths

### Path A: Executive Briefing (15 minutes)
1. ADR-model-centralization.md — Decision summary
2. model-centralization-design-summary.md — Key decisions section

**Output:** Understand decision, rationale, consequences

---

### Path B: Team Context (30 minutes)
1. model-centralization-design-summary.md — Entire document
2. architecture-model-centralization.md — Current state & architecture sections

**Output:** Understand problem, solution, impact

---

### Path C: Engineer Preparation (2 hours)
1. model-centralization-design-summary.md — Full read
2. architecture-model-centralization.md — Full read
3. model-implementation-roadmap.md — Scan all phases
4. Create implementation checklist

**Output:** Ready to implement Phase 1 tasks

---

### Path D: Deep Technical Review (4 hours)
1. architecture-model-centralization.md — Full read
2. model-implementation-roadmap.md — Full read
3. Cross-reference technical specs with models.yaml
4. Review Phase 1 task details

**Output:** Complete technical understanding

---

## Key Concepts

### Single Source of Truth
- **File:** models.yaml
- **Contains:** Role → model mappings, provider variants, capability matrix
- **Used by:** Rendering pipeline, documentation generator, validation script

### Role-Based Indirection
- Agent files reference roles (engineer, senior_engineer, etc.)
- Actual model names resolved at build time
- Enables provider-specific rendering without source changes

### ModelResolver Class
- **Location:** src/models/resolver.py (to create)
- **Core method:** `resolve(role, provider) → model_name`
- **Features:** env overrides, capability detection, fallback logic

### Environment Overrides
```bash
AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7        # Override specific
MODEL_TIER=haiku                                      # Cost-saving
PREFERRED_PROVIDER=copilot                            # Provider preference
```

### 13 Agent Roles
```
engineer, senior_engineer, quality_engineer, lead_engineer,
security_engineer, principal_engineer, model_engineer,
general_orchestrator, metrics, testing, spec_engineer,
healing_engineer, spec_engineer_orchestrator
```

---

## File Changes Summary

### New Files to Create (9)
```
src/models/
  ├── resolver.py
  ├── defaults.py
  ├── validate.py
  ├── schema.json
  └── __init__.py
tests/
  ├── test_model_resolver.py
  ├── test_provider_resolution.py
  └── test_env_overrides.py
render/
  └── doc_generator.py
docs/
  └── model-management.md
```

### Files to Modify (16+)
```
src/agents/*.md (13 files)           — model: → role:
models.yaml                          — Enhanced
renderer/scripts/render-copilot-agents.py
docs/SPEC.md
docs/INSTALL.md
Makefile
```

---

## Timeline

- **Phase 1:** 2 days (Foundation)
- **Phase 2:** 3 days (Agent Frontmatter)
- **Phase 3:** 2 days (Copilot CLI)
- **Phase 4:** 3 days (Documentation)
- **Phase 5:** 2 days (Testing)
- **Phase 6:** 1.5 days (Operations)
- **Phase 7:** 1 day (Cleanup)
- **TOTAL:** 14.5 days work = 3-4 weeks real-world

---

## Success Criteria

### Quantitative ✓
- [ ] Zero hard-coded models in src/agents/ (verified by grep)
- [ ] 100% agents have valid roles in models.yaml
- [ ] All CI/CD validation passing
- [ ] Documentation auto-generated from models.yaml

### Qualitative ✓
- [ ] Easy to test models (1 env var)
- [ ] Easy to add roles (documented)
- [ ] Team confident in assignments
- [ ] Reduced maintenance burden

---

## How to Use This Index

1. **First Time?** → Read "Quick Navigation" section above
2. **Need specific info?** → Use "Document Overview" to find right file
3. **Planning to implement?** → Follow "Path C: Engineer Preparation"
4. **Reviewing design?** → Follow "Path D: Deep Technical Review"
5. **Have a question?** → Check "Key Concepts" section
6. **Need task details?** → Go to model-implementation-roadmap.md

---

## Questions?

- **"Why this approach?"** → See ADR-model-centralization.md (Decision section)
- **"How does it work?"** → See architecture-model-centralization.md (Architecture Design)
- **"What do I implement?"** → See model-implementation-roadmap.md (Phases & Tasks)
- **"What changes?"** → See model-centralization-design-summary.md (File Changes)

---

## Document Status

| Document | Status | Owner | Last Updated |
|----------|--------|-------|--------------|
| ADR-model-centralization.md | ✅ APPROVED | Principal | 2025-05-15 |
| architecture-model-centralization.md | ✅ COMPLETE | Principal | 2025-05-15 |
| model-implementation-roadmap.md | ✅ COMPLETE | Principal | 2025-05-15 |
| model-centralization-design-summary.md | ✅ COMPLETE | Principal | 2025-05-15 |
| MODEL-CENTRALIZATION-INDEX.md | ✅ COMPLETE | Principal | 2025-05-15 |

---

**Ready for Implementation** ✅  
**Approved for Handoff** ✅  
**All Documentation Complete** ✅

