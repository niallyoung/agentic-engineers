---
title: Model Centralization Implementation Roadmap
type: Implementation Plan
phase: Ready for Execution
created: 2025-05-15
---

# Implementation Roadmap: Model Centralization

## Overview

This roadmap translates the Model Centralization Architecture design into executable tasks. It follows the 7-phase approach outlined in the architecture document, with specific acceptance criteria and dependencies.

**Total Estimated Effort:** 3-4 weeks  
**Team Size:** 1 Engineer (with Principal Engineer oversight)  
**Risk Level:** Medium (affects agent rendering, requires CI/CD validation)

---

## Phase 1: Foundation (2 days)

### Task 1.1: Create ModelResolver Class

**Title:** Implement centralized model resolution layer  
**Type:** Feature  
**Story Points:** 3  
**Time Estimate:** 2 hours

**Acceptance Criteria:**
- [ ] `src/models/resolver.py` created with ModelResolver class
- [ ] Core methods implemented: `resolve()`, `get_canonical()`, `get_effort()`
- [ ] Reads models.yaml successfully
- [ ] Returns correct model for given role and provider
- [ ] Unit tests pass (test_model_resolver.py)
- [ ] Handles missing roles gracefully (raises ValueError with clear message)

**Implementation Notes:**
```python
# src/models/resolver.py
class ModelResolver:
    def __init__(self, models_yaml: str = None):
        # Load models.yaml, handle file not found
        
    def resolve(self, role: str, provider: str = None) -> str:
        # Core resolution logic per architecture
        
    def get_canonical(self, role: str) -> str:
        # Return canonical form
        
    def get_effort(self, role: str) -> str:
        # Return effort level for cost tracking
```

**Dependencies:** None  
**Blocking:** All other tasks in Phase 1  
**QA Checklist:**
- [ ] Can resolve all 13 agent roles
- [ ] Returns correct provider-specific models
- [ ] Fallback to canonical works
- [ ] Error messages are helpful

**Owner:** Engineer  
**Reviewer:** Principal Engineer

---

### Task 1.2: Add Environment Override Support

**Title:** Implement env var precedence logic  
**Type:** Feature  
**Story Points:** 2  
**Time Estimate:** 1.5 hours

**Acceptance Criteria:**
- [ ] `resolve_with_env()` method added to ModelResolver
- [ ] Checks AGENT_MODEL_OVERRIDE_{ROLE} (highest precedence)
- [ ] Checks MODEL_TIER (applies tier fallback)
- [ ] Checks PREFERRED_PROVIDER (uses provider variant)
- [ ] Falls back to models.yaml canonical
- [ ] Unit tests cover all override scenarios
- [ ] Documentation added to resolver.py docstring

**Implementation Notes:**
```python
# Environment variable precedence (highest to lowest):
1. AGENT_MODEL_OVERRIDE_{ROLE} = "claude-sonnet-4.6"
2. MODEL_TIER = "haiku" (downgrade all to haiku tier)
3. PREFERRED_PROVIDER = "copilot" (use copilot provider models)
4. models.yaml['role']['providers'][provider]
5. models.yaml['role']['canonical']
```

**Test Scenarios:**
- Override single role
- Override all with tier
- Invalid override (should fallback)
- Provider not in registry (should fallback to canonical)

**Dependencies:** Task 1.1  
**Blocking:** Phase 2  
**Owner:** Engineer

---

### Task 1.3: Validate and Enhance models.yaml

**Title:** Audit and validate model registry  
**Type:** Quality  
**Story Points:** 2  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] All 13 agent roles verified in models.yaml
- [ ] Missing entries added (if any)
- [ ] Provider coverage verified (at least 1 provider per role)
- [ ] JSON Schema validation created (src/models/schema.json)
- [ ] models.yaml passes schema validation
- [ ] Documentation updated with new entries

**Validation Checklist:**
```
✓ engineer → claude-haiku (canonical)
✓ senior_engineer → claude-sonnet
✓ quality_engineer → claude-sonnet
✓ lead_engineer → claude-sonnet
✓ security_engineer → claude-opus
✓ principal_engineer → claude-opus
✓ model_engineer → claude-haiku
✓ orchestrator → claude-haiku
✓ general_orchestrator → claude-haiku (alias)
✓ metrics → claude-haiku
✓ testing → claude-haiku
✓ spec_engineer → claude-sonnet
✓ healing_engineer → claude-sonnet
✓ spec_engineer_orchestrator → claude-sonnet
```

**JSON Schema Location:** `src/models/schema.json`

**Dependencies:** None  
**Owner:** Principal Engineer (review), Engineer (execution)

---

## Phase 2: Agent Frontmatter Refactoring (3 days)

### Task 2.1: Update Agent Frontmatter (All 13 Files)

**Title:** Convert hard-coded models to role references  
**Type:** Refactoring  
**Story Points:** 3  
**Time Estimate:** 1.5 hours

**Acceptance Criteria:**
- [ ] All 13 agent files updated
- [ ] `model: claude-X-Y.Z` replaced with `role: agent_name`
- [ ] Role values match models.yaml entries exactly
- [ ] No hard-coded models remain in frontmatter
- [ ] All frontmatter still contains: name, description, role
- [ ] Files validated against JSON schema

**Changes per Agent:**

| File | Old | New |
|------|-----|-----|
| engineer.md | `model: claude-haiku-4.5` | `role: engineer` |
| senior-engineer.md | `model: claude-sonnet-4.6` | `role: senior_engineer` |
| quality-engineer.md | `model: claude-sonnet-4.6` | `role: quality_engineer` |
| lead-engineer.md | `model: claude-sonnet-4.6` | `role: lead_engineer` |
| security-engineer.md | `model: claude-opus-4.7` | `role: security_engineer` |
| principal-engineer.md | `model: claude-opus-4.7` | `role: principal_engineer` |
| model-engineer.md | `model: claude-sonnet-4.6` | `role: model_engineer` |
| orchestrator.md | `model: claude-haiku-4.5` | `role: general_orchestrator` |
| metrics.md | `model: claude-haiku-4.5` | `role: metrics` |
| testing.md | `model: claude-haiku-4.5` | `role: testing` |
| spec-engineer.md | `model: claude-sonnet-4.6` | `role: spec_engineer` |
| healing-engineer.md | `model: claude-sonnet-4.6` | `role: healing_engineer` |
| spec-engineer-orchestrator.md | `model: claude-sonnet-4.6` | `role: spec_engineer_orchestrator` |

**Validation Step:**
```bash
# For each file, verify:
grep "^role:" src/agents/*.md  # Should all exist
grep "^model:" src/agents/*.md  # Should NOT exist (except README)
```

**Dependencies:** Task 1.3  
**Blocking:** Task 2.2  
**Owner:** Engineer

---

### Task 2.2: Update Render Pipeline

**Title:** Integrate ModelResolver into rendering  
**Type:** Feature  
**Story Points:** 3  
**Time Estimate:** 2 hours

**Acceptance Criteria:**
- [ ] `render-copilot-agents.py` updated to use ModelResolver
- [ ] Reads `role` from agent frontmatter
- [ ] Resolves to model name using ModelResolver
- [ ] Injects resolved model into output frontmatter
- [ ] Integration tests pass
- [ ] Provider-specific rendering works correctly

**Modified Files:**
- `renderer/scripts/render-copilot-agents.py`
- `render/main.py` (if applicable)

**Rendering Logic:**
```
For each src/agents/*.md:
  1. Read frontmatter
  2. Extract role: "engineer"
  3. Call resolver.resolve(role, provider="claude")
  4. Get model: "claude-haiku-4.5"
  5. Create ~/.copilot/agents/X.agent.md with model in frontmatter
```

**Test Cases:**
- Claude rendering (dot notation)
- Copilot rendering (GPT models)
- Missing provider fallback
- All 13 agents render correctly

**Dependencies:** Task 2.1  
**Owner:** Engineer

---

## Phase 3: Copilot CLI Provider Rendering (2 days)

### Task 3.1: Implement Copilot Provider Rendering

**Title:** Add Copilot-specific model resolution  
**Type:** Feature  
**Story Points:** 2  
**Time Estimate:** 2 hours

**Acceptance Criteria:**
- [ ] Copilot agents render with GPT models (not Claude)
- [ ] models.yaml['role']['providers']['copilot'] used
- [ ] ~/.copilot/agents/*.agent.md have correct models
- [ ] Examples:
  - Engineer: `model: gpt-4o-mini` (not claude-haiku-4.5)
  - Senior Engineer: `model: gpt-4` (not claude-sonnet-4.6)
  - Security Engineer: `model: gpt-4o` (not claude-opus-4.7)
- [ ] Manual test: Copilot agents work correctly

**Manual Test Steps:**
```bash
# Render Copilot agents
python renderer/scripts/render-copilot-agents.py

# Verify output
grep "model:" ~/.copilot/agents/*.agent.md

# Should see GPT models, not Claude
grep "claude" ~/.copilot/agents/*.agent.md  # Should NOT find any
```

**Dependencies:** Task 2.2  
**Owner:** Engineer

---

### Task 3.2: Test Provider Consistency

**Title:** Validate provider-specific rendering  
**Type:** QA  
**Story Points:** 2  
**Time Estimate:** 1.5 hours

**Acceptance Criteria:**
- [ ] All Claude agents use Claude models
- [ ] All Copilot agents use GPT models
- [ ] Fallback tested (provider not in registry)
- [ ] Capability deltas logged correctly
- [ ] Integration tests pass
- [ ] No regressions in agent behavior

**Test Matrix:**

| Agent | Claude Model | Copilot Model | Status |
|-------|-------------|--------------|--------|
| Engineer | claude-haiku-4.5 | gpt-4o-mini | ✓ |
| Senior Engineer | claude-sonnet-4.6 | gpt-4 | ✓ |
| Quality Engineer | claude-sonnet-4.6 | gpt-4 | ✓ |
| Lead Engineer | claude-sonnet-4.6 | gpt-4 | ✓ |
| Security Engineer | claude-opus-4.7 | gpt-4o | ✓ |
| Principal Engineer | claude-opus-4.7 | gpt-4o | ✓ |
| Model Engineer | claude-haiku-4.5 | gpt-4o-mini | ✓ |
| Orchestrator | claude-haiku-4.5 | gpt-4o-mini | ✓ |

**Dependencies:** Task 3.1  
**Owner:** QA Engineer or Engineer

---

## Phase 4: Documentation Cleanup (3 days)

### Task 4.1: Create Documentation Generator

**Title:** Build doc generation from models.yaml  
**Type:** Feature  
**Story Points:** 3  
**Time Estimate:** 2 hours

**Acceptance Criteria:**
- [ ] `render/doc_generator.py` created
- [ ] Reads models.yaml
- [ ] Generates:
  - Agent table (role → model → effort)
  - Provider table (provider → capabilities)
  - Model reference tables
- [ ] Output markdown format
- [ ] Used by docs/SPEC.md and docs/README.md
- [ ] Handles missing data gracefully

**Generated Artifacts:**
```
render/
├── doc_generator.py        # Generates from models.yaml
└── output/
    ├── agent_table.md      # All agents with models
    ├── provider_table.md   # Provider capabilities
    └── model_reference.md  # Version & format guide
```

**Dependencies:** Task 1.1  
**Owner:** Engineer

---

### Task 4.2: Update docs/SPEC.md

**Title:** Remove hard-coded models, use generation  
**Type:** Refactoring  
**Story Points:** 2  
**Time Estimate:** 1.5 hours

**Acceptance Criteria:**
- [ ] Hard-coded model references removed
- [ ] Tables generated from models.yaml
- [ ] Format consistency: use dot notation (4.5, not 4-5)
- [ ] Links to models.yaml added for canonical truth
- [ ] All agent descriptions match source files
- [ ] CI/CD validates generation matches file

**Changes:**
- Replace hard-coded tables with generated ones
- Add generation script to build pipeline
- Document that SPEC.md is generated (not edited)

**Validation:**
```bash
# Verify no hard-coded models remain
grep -n "claude-\|gpt-" docs/SPEC.md  # Should only find generated content
```

**Dependencies:** Task 4.1  
**Owner:** Engineer

---

### Task 4.3: Update src/agents/README.md

**Title:** Update agent documentation with model management  
**Type:** Documentation  
**Story Points:** 1  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] Remove hard-coded model examples
- [ ] Add section: "Model Assignment" linking to models.yaml
- [ ] Document role → model mapping rule
- [ ] Add "Viewing Current Models" instructions
- [ ] Include "Overriding Models" environment variable examples
- [ ] Link to architecture-model-centralization.md

**New Sections:**
1. Model Assignment (how roles map to models)
2. Viewing Current Models (query models.yaml)
3. Overriding Models (AGENT_MODEL_OVERRIDE examples)

**Dependencies:** Task 4.1  
**Owner:** Engineer

---

## Phase 5: Testing & Validation (2 days)

### Task 5.1: Integration Tests

**Title:** Test full resolution pipeline  
**Type:** Testing  
**Story Points:** 3  
**Time Estimate:** 3 hours

**Acceptance Criteria:**
- [ ] `tests/test_model_resolver.py` created
- [ ] `tests/test_provider_resolution.py` created
- [ ] `tests/test_env_overrides.py` created
- [ ] All 13 agent roles resolve correctly
- [ ] Provider-specific resolution works
- [ ] Environment overrides take precedence
- [ ] Fallback scenarios tested
- [ ] 100% test coverage on resolver.py
- [ ] All tests passing

**Test Suites:**

**test_model_resolver.py:**
```python
def test_resolve_engineer_to_haiku(): ...
def test_resolve_senior_engineer_to_sonnet(): ...
def test_get_effort_levels(): ...
def test_canonical_models(): ...
def test_missing_role_raises_error(): ...
def test_fallback_to_canonical(): ...
```

**test_provider_resolution.py:**
```python
def test_claude_provider_models(): ...
def test_copilot_provider_models(): ...
def test_missing_provider_fallback(): ...
def test_get_capability_deltas(): ...
def test_thinking_mode_detection(): ...
```

**test_env_overrides.py:**
```python
def test_agent_model_override_single_role(): ...
def test_model_tier_override(): ...
def test_preferred_provider_override(): ...
def test_override_precedence(): ...
def test_invalid_override_fallback(): ...
```

**Dependencies:** All Phase 1-4 tasks  
**Owner:** QA Engineer or Engineer

---

### Task 5.2: Validation Script

**Title:** Create codebase validation  
**Type:** Quality  
**Story Points:** 2  
**Time Estimate:** 2 hours

**Acceptance Criteria:**
- [ ] `src/models/validate.py` created
- [ ] Checks:
  1. All agent files have valid roles
  2. All roles in models.yaml are documented
  3. No hard-coded models in agent files
  4. No hard-coded models in SPEC.md (except generated)
  5. Format consistency (dots vs dashes)
  6. Role → file mapping is 1:1
- [ ] Returns exit code 0 on success, 1 on failure
- [ ] Clear error messages for failures
- [ ] Can be run locally: `python src/models/validate.py`

**Validation Rules:**
```
✓ src/agents/*.md (except README) must have role field
✗ src/agents/*.md must NOT have model field
✗ docs/SPEC.md must NOT have claude-X-Y-Z or gpt-X patterns (except in generated tables)
✓ Role field value must exist in models.yaml
✓ All roles in models.yaml should have >= 1 agent file
✓ Frontmatter format matches JSON schema
```

**Usage:**
```bash
python src/models/validate.py
# Output: ✓ All validations passed or ✗ Violations found
```

**Dependencies:** All Phase 1-4 tasks  
**Owner:** Engineer

---

### Task 5.3: Update make verify Target

**Title:** Add model validation to CI/CD  
**Type:** CI/CD  
**Story Points:** 1  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] `make verify` includes model validation
- [ ] Validation runs as part of CI/CD pipeline
- [ ] Fails build if validation fails
- [ ] Clear error messages in CI logs
- [ ] Documentation updated (Makefile comments)

**Makefile Changes:**
```makefile
verify: validate-models lint test
@echo "✓ All verification steps passed"

validate-models:
python src/models/validate.py

.PHONY: verify validate-models
```

**Dependencies:** Task 5.2  
**Owner:** Engineer

---

## Phase 6: Operational Documentation (1.5 days)

### Task 6.1: Create Model Management Guide

**Title:** Write operational documentation  
**Type:** Documentation  
**Story Points:** 2  
**Time Estimate:** 2 hours

**Location:** `docs/model-management.md`

**Acceptance Criteria:**
- [ ] Document created
- [ ] Covers: What, Why, How, When
- [ ] Step-by-step instructions for:
  1. Adding a new role
  2. Updating model assignments
  3. Setting environment overrides
  4. Verifying model assignments
  5. Troubleshooting resolution
- [ ] Examples provided for each scenario
- [ ] FAQ section

**Sections:**
1. **Overview** - What is model centralization?
2. **Architecture** - How it works (high-level)
3. **Models Registry** - models.yaml structure
4. **Common Tasks**
   - View current assignments
   - Add new role
   - Update existing model
   - Test different model
5. **Environment Overrides**
   - AGENT_MODEL_OVERRIDE_{ROLE}
   - MODEL_TIER
   - PREFERRED_PROVIDER
6. **Troubleshooting**
   - Model not resolving
   - Provider not found
   - Invalid override
7. **FAQ**

**Dependencies:** All Phase 1-5 tasks  
**Owner:** Principal Engineer or Senior Engineer

---

### Task 6.2: Update INSTALL.md

**Title:** Add model management section  
**Type:** Documentation  
**Story Points:** 1  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] INSTALL.md updated
- [ ] New section: "Model Configuration"
- [ ] Environment variable options documented
- [ ] Examples showing:
  - Default setup
  - Copilot override
  - Cost-saving mode
  - Testing mode
- [ ] Link to docs/model-management.md

**New Section:**
```markdown
## Model Configuration

By default, models are assigned per role in models.yaml.

### Environment Overrides

Override defaults with environment variables:

- `AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7` - Override specific agent
- `MODEL_TIER=haiku` - Use Haiku tier for all agents (cost-saving)
- `PREFERRED_PROVIDER=copilot` - Use Copilot CLI models (GPT-4)

See docs/model-management.md for details.
```

**Dependencies:** Task 6.1  
**Owner:** Engineer

---

## Phase 7: Deprecation & Cleanup (1 day)

### Task 7.1: Mark Old Patterns as Deprecated

**Title:** Document migration path  
**Type:** Maintenance  
**Story Points:** 1  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] Comments added to deprecated patterns
- [ ] Migration instructions provided
- [ ] Timeline documented (if applicable)
- [ ] Links to new approach

**Deprecated Patterns:**
1. Hard-coded model in agent frontmatter
2. Hand-edited SPEC.md model tables
3. Provider-specific model overrides outside models.yaml

**Marker Format:**
```python
# DEPRECATED: Hard-coded models in agent frontmatter
# Use: role field + ModelResolver instead
# Migration: See docs/model-management.md
```

**Dependencies:** Phase 1-6  
**Owner:** Principal Engineer

---

### Task 7.2: Final Audit

**Title:** Verify complete centralization  
**Type:** Quality  
**Story Points:** 1  
**Time Estimate:** 1 hour

**Acceptance Criteria:**
- [ ] Codebase grep for hard-coded models: 0 results (except defaults)
- [ ] All files validate against schema
- [ ] Documentation generated correctly
- [ ] CI/CD pipeline passes
- [ ] No regressions in agent behavior
- [ ] All 13 agents render correctly
- [ ] Copilot CLI agents work as expected

**Audit Checklist:**
```bash
# Should return ONLY embedded defaults, no hard-coded references
grep -r "claude-opus-4.7\|claude-sonnet-4.6\|claude-haiku-4.5" src/agents/

# Should return 0 results except in fallback defaults
grep -r "model:" src/agents/*.md | grep -v "^Binary"

# Should pass with 0 violations
python src/models/validate.py
```

**Post-Audit:**
- [ ] Update CHANGELOG
- [ ] Create release notes
- [ ] Tag commit with version
- [ ] Deploy to production

**Dependencies:** Phase 1-6  
**Owner:** Principal Engineer (final sign-off)

---

## Timeline Overview

```
Phase 1 (Foundation)           [==] 2 days
  Task 1.1-1.3                 concurrent

Phase 2 (Frontmatter)         [===] 3 days
  Task 2.1 (1.5h)
  Task 2.2 (2h)               depends on 2.1

Phase 3 (Copilot)             [==] 2 days
  Task 3.1 (2h)
  Task 3.2 (1.5h)             depends on 3.1

Phase 4 (Documentation)       [===] 3 days
  Task 4.1 (2h)
  Task 4.2 (1.5h)             depends on 4.1
  Task 4.3 (1h)               depends on 4.1

Phase 5 (Testing)             [==] 2 days
  Task 5.1-5.3                all depend on Phase 1-4

Phase 6 (Documentation)       [=] 1.5 days
  Task 6.1 (2h)
  Task 6.2 (1h)               depends on 6.1

Phase 7 (Cleanup)             [=] 1 day
  Task 7.1-7.2

TOTAL:                         ~3-4 weeks
```

---

## Success Criteria (Final)

### Quantitative Measures
- [ ] Zero hard-coded model names in src/agents/ (verified by grep)
- [ ] 100% of agent files reference valid roles in models.yaml
- [ ] All CI/CD validation tests passing
- [ ] Documentation auto-generated from single source
- [ ] 0 regressions in agent behavior
- [ ] All 13 agents render and function correctly

### Qualitative Measures
- [ ] Easy to add new roles (< 5 minutes, documented)
- [ ] Easy to test different models (single env var, documented)
- [ ] Team understands centralized model strategy
- [ ] Reduced maintenance burden for future model updates
- [ ] Consistent format across all documentation

### Sign-Off
- Principal Engineer reviews architecture and implementation
- All tests passing
- Documentation complete and reviewed
- Ready for production deployment

---

## References

- Architecture Document: docs/architecture-model-centralization.md
- Models Registry: models.yaml
- Existing Resolver: render/main.py (ModelResolver class)
- Agent Definitions: src/agents/*.md

