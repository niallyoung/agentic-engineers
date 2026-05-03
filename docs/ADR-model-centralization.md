---
title: Architecture Decision Record - Model Centralization
type: ADR
decision: APPROVED
date: 2025-05-15
---

# ADR: Centralized Model Naming Architecture

## Status
**APPROVED** — Ready for implementation

## Context

### Problem Statement
The agentic-engineers codebase has hard-coded model references scattered across multiple files:
1. **src/agents/*.md** — 13 agent definition files with hard-coded models in YAML frontmatter
2. **docs/SPEC.md** — Multiple tables with hard-coded model references
3. **~/.copilot/agents/** — Copilot CLI agents with duplicated model definitions
4. **src/agents/README.md** — Example references to specific models

This creates **high maintenance burden**: changing a model requires updates in 3+ locations, with risk of inconsistency.

### Current State
- **models.yaml** exists with comprehensive role → model mappings but is NOT being used
- Agent files use dot notation (claude-haiku-4.5) inconsistently
- No mechanism for environment-specific overrides
- No format conversion strategy between agentic-engineers and Copilot CLI
- render/main.py has partial ModelResolver implementation but not integrated

### Success Criteria
1. Single source of truth for model assignments
2. Format conversion strategy documented
3. Zero code duplication of model names
4. Environment-specific overrides supported
5. Implementation roadmap provided

## Decision

### Architecture

Implement a **centralized model naming system** with these components:

1. **Single Source of Truth**
   - models.yaml becomes the canonical model registry
   - Defines role → model mappings for all providers
   - Specifies capability deltas (thinking, structured output, context window)

2. **Format Conversion Layer**
   - ModelResolver class (src/models/resolver.py)
   - Converts role → provider-specific model name
   - Handles format conversion (canonical ↔ provider-specific)
   - Supports environment variable overrides

3. **Role-Based Frontmatter**
   - Agent files reference roles (not hard-coded models)
   - Renderer resolves roles to models at build time
   - Enables format/provider-specific rendering

4. **Environment Overrides**
   - AGENT_MODEL_OVERRIDE_{ROLE} — Override specific agent
   - MODEL_TIER — Apply tier fallback (haiku/sonnet/opus)
   - PREFERRED_PROVIDER — Use provider-specific models
   - Session-level overrides supported

5. **Fallback Strategy**
   - Provider not found → fall back to canonical
   - Missing role → embedded defaults + warning
   - Invalid override → fall back to canonical + warning
   - Graceful degradation throughout

### Integration Points

| Component | Current | New | Owner |
|-----------|---------|-----|-------|
| src/agents/*.md | Hard-coded model: | role: | Engineer |
| render-copilot-agents.py | Direct copy | Use ModelResolver | Engineer |
| docs/SPEC.md | Hand-edited tables | Generated from models.yaml | Engineer |
| ~/.copilot/agents/ | Claude models | Provider-specific (GPT) | Engineer |
| CI/CD pipeline | No validation | Validation script added | Engineer |

### Changes Required

**Phase 1: Foundation (2 days)**
- Create ModelResolver class with core logic
- Add environment override support
- Validate/enhance models.yaml

**Phase 2: Agent Refactoring (3 days)**
- Update all 13 agent files (role field)
- Integrate ModelResolver into render pipeline

**Phase 3: Provider Rendering (2 days)**
- Implement Copilot provider-specific rendering
- Test provider consistency

**Phase 4: Documentation (3 days)**
- Create documentation generator
- Update SPEC.md and README.md
- Remove hard-coded references

**Phase 5-7: Testing & Cleanup (4 days)**
- Integration tests, validation, CI/CD
- Operational documentation
- Final audit

**Total Effort:** 3-4 weeks (1 Engineer + Principal Engineer oversight)

## Rationale

### Why This Approach?

**1. Single Source of Truth**
- models.yaml already exists with well-structured role mappings
- Eliminates duplication, reduces maintenance burden
- Easy to find and update all model assignments

**2. Role-Based Indirection**
- Agent files reference logical roles (engineer, senior_engineer, etc.)
- Actual model names resolved at build time
- Enables format and provider-specific rendering without touching source files

**3. Format Conversion Layer (ModelResolver)**
- Separates resolution logic from rendering
- Reusable across different contexts (agents, docs, tests)
- Enables testing different models without code changes

**4. Environment Overrides**
- Supports testing without permanent changes
- Cost-saving modes (downgrade to cheaper models)
- Session-level overrides without modifying files

**5. Graceful Fallback**
- Missing provider → fall back to canonical (still works)
- Invalid override → fall back to known-good model
- No hard failures due to configuration issues

### Why Now?

**Triggers:**
1. models.yaml exists but unused — waste of effort
2. Hard-coded models scattered — maintenance debt building
3. Copilot CLI rendering starting — multiplying duplication
4. Need for testing different models — environment overrides critical
5. Cost optimization efforts starting — need flexible tier selection

**Cost of Waiting:**
- Every new agent file gets hard-coded models
- Every model update touches 3+ files
- Documentation falls out of sync with code
- Testing different models becomes manual and error-prone

## Alternatives Considered

### Alternative 1: Distributed Model Management
- Keep models in each agent file
- Update render script to detect pattern and convert
- **Rejected:** Still requires changes to 13 files, no centralization benefit

### Alternative 2: Compile-Time Substitution
- Keep models.yaml but use sed/awk to inject into files
- **Rejected:** Harder to troubleshoot, no role indirection benefit, doesn't support overrides

### Alternative 3: Runtime Resolution Only
- No changes to agent files
- Full resolution at runtime with Orchestrator
- **Rejected:** Breaks Copilot CLI agents, no documentation generation

### Selected: Role-Based + Build-Time + Runtime
- Combines benefits of all alternatives
- Single source (models.yaml)
- Build-time rendering (works with Copilot)
- Runtime overrides (testing + cost management)
- Fallback strategy (robustness)

## Consequences

### Positive
1. ✅ Single source of truth for model assignments
2. ✅ Reduced maintenance burden for future changes
3. ✅ Ability to test models via environment variables
4. ✅ Consistent documentation (auto-generated)
5. ✅ Provider-specific rendering (Copilot gets GPT, Claude gets Claude)
6. ✅ Graceful fallback if config incomplete
7. ✅ Cost optimization tools (tier downgrade, provider preference)
8. ✅ Enables future model testing framework

### Negative
1. ⚠️ Requires refactoring 13 agent files (1.5 hours work)
2. ⚠️ Render pipeline must be modified (2 hours work)
3. ⚠️ New dependency: src/models/resolver.py
4. ⚠️ Build-time logic: models.yaml must be present
5. ⚠️ Learning curve for environment overrides

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| models.yaml becomes out-of-sync | Agent assignments wrong | Validation in CI/CD, clear ownership |
| Provider not in models.yaml | Falls back to canonical | Error message, explicit override required |
| Hard-coded models persist | Defeats goal | Grep checks in pre-commit hook, linting |
| Rendering breaks | Agents don't deploy | Dual-mode support during transition |
| Confusion about resolution | Wrong model used | Documentation, debug logging in resolver |

## Implementation

See: docs/model-implementation-roadmap.md

**Key Milestones:**
1. ModelResolver implementation + tests (Phase 1)
2. Agent frontmatter refactoring (Phase 2)
3. Copilot rendering working (Phase 3)
4. Documentation generation (Phase 4)
5. CI/CD validation (Phase 5)
6. All tests passing (Phase 5)
7. Final audit & cleanup (Phase 7)

## Success Metrics

### Quantitative
- [ ] 0 hard-coded model names in src/agents/ (grep verified)
- [ ] 100% valid role references in models.yaml
- [ ] 100% CI/CD validation passing
- [ ] Documentation auto-generated from single source

### Qualitative
- [ ] Team confident in model management
- [ ] Easy to test different models (1 env var)
- [ ] Easy to add new roles (documented)
- [ ] Reduced confusion about which model is used

## Review & Approval

**Principal Engineer Review:**
- [ ] Architecture sound and complete
- [ ] All alternatives considered
- [ ] Risks mitigated
- [ ] Implementation roadmap clear
- [ ] Success metrics achievable

**Team Sign-Off:**
- [ ] Engineering consensus on approach
- [ ] No blocking concerns
- [ ] Resources available (1 Engineer, 3-4 weeks)

---

## Appendix: Quick Reference

### Key Files
- **models.yaml** — Single source of truth
- **src/models/resolver.py** — Resolution logic (new)
- **src/agents/*.md** — Use role field (refactored)
- **docs/architecture-model-centralization.md** — Full architecture
- **docs/model-implementation-roadmap.md** — Detailed tasks

### Role to Model Mapping
```yaml
engineer: claude-haiku-4.5
senior_engineer: claude-sonnet-4.6
security_engineer: claude-opus-4.7
principal_engineer: claude-opus-4.7
# ... see models.yaml for complete list
```

### Environment Variables
```bash
AGENT_MODEL_OVERRIDE_ENGINEER=claude-sonnet-4.6  # Override specific
MODEL_TIER=haiku                                  # Cost-saving mode
PREFERRED_PROVIDER=copilot                        # Use GPT models
```

### Validation
```bash
python src/models/validate.py  # Check consistency
make verify                     # Full CI/CD validation
```

