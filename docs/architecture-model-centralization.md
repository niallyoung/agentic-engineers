---
title: Model Centralization Architecture
type: Architecture Decision Record
date: 2025-05-15
status: Design
phase: Implementation Planning
---

# Model Centralization Architecture

## Executive Summary

This document designs a **centralized model naming and assignment strategy** to eliminate hard-coded model references scattered across the agentic-engineers codebase. The solution provides a single source of truth (`models.yaml`) that defines role-to-model mappings, supports format conversion across providers (agentic-engineers dot notation ↔ Copilot CLI format), and enables environment-specific overrides and fallback strategies.

**Problem Statement:**
- 13 agent definitions with hard-coded models in YAML frontmatter
- docs/SPEC.md contains scattered hard-coded model references
- models.yaml exists but is not being actively used
- Copilot CLI agents are rendered from source but duplicated model definitions
- Maintenance burden: changing a model requires updates in multiple files
- No mechanism for environment-specific overrides or testing different models

**Success Criteria:**
1. Single source of truth for model assignments (models.yaml)
2. Format conversion strategy documented and implementable
3. Role → model mapping formalized and validated
4. Environment-specific override mechanism specified
5. Fallback and default strategies defined
6. Implementation roadmap provided
7. Zero code duplication of model names after implementation

---

## Current State Analysis

### Existing Models Registry (models.yaml)

**Status:** EXISTS but UNUSED

```yaml
role_models:
  engineer:
    canonical: "claude-haiku"
    thinking: false
    effort: "high"
    providers:
      copilot: "gpt-4o-mini"
      claude: "claude-haiku-4.5"
      openai: "gpt-4o-mini"
      google: "gemini-2.0-flash"
      meta: "llama-3-8b"
```

**Good aspects:**
- Well-structured YAML with role → model mappings
- Provider-specific variants defined for each role
- Metadata (thinking, effort) captured
- Provider capabilities documented

**Problems:**
- Not integrated into agent definition workflow
- Agent frontmatter still uses hard-coded models
- No layer integrating model resolution with agent rendering

### Hard-Coded Model References

**Location 1: src/agents/*.md (13 files)**
```yaml
---
name: Engineer
model: claude-haiku-4.5  # ← Hard-coded
---
```

Current state: All 13 agent files have explicit model frontmatter. They use Claude models (dot notation).

**Location 2: ~/.copilot/agents/*.agent.md**
```yaml
model: claude-haiku-4.5  # ← Same hard-coded value
```

Generated from src/agents/ by render-copilot-agents.py. Currently mirrors source files exactly.

**Location 3: docs/SPEC.md**
```markdown
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 | Entry point... |
| **Engineer** | claude-haiku-4-5 | high | $0.03 | Execute well-scoped... |
```

Multiple tables with hard-coded models. Different dash format (4-5 vs 4.5).

**Location 4: src/agents/README.md**
```markdown
| **Haiku** | 1x | Well-scoped work | engineer, orchestrator, metrics, testing |
```

Example references to model tiers and agent assignments.

### Existing Infrastructure

**render/main.py** exists with ModelResolver class:
- Reads models.yaml
- Resolves role → provider-specific model
- Has fallback logic (canonical if provider not specified)
- Has delta detection (capability gaps)

**Status:** Partially implemented but not integrated into agent pipeline.

---

## Architecture Design

### 1. Centralized Model Configuration

**Single Source of Truth: models.yaml**

The models.yaml file becomes the canonical reference for ALL model assignments. Structure (as exists today):

```yaml
---
# CANONICAL MODEL REGISTRY - Single Source of Truth
# Maps roles to models across all providers

role_models:
  engineer:
    canonical: "claude-haiku"      # Generic canonical form
    thinking: false                 # Requires thinking mode?
    effort: "high"                 # Token/cost effort level
    providers:
      copilot: "gpt-4o-mini"       # Provider-specific names
      claude: "claude-haiku-4.5"
      openai: "gpt-4o-mini"
      google: "gemini-2.0-flash"
      meta: "llama-3-8b"
    description: "Execution specialist..."
  
  senior_engineer:
    canonical: "claude-sonnet"
    thinking: true
    effort: "high"
    providers:
      copilot: "gpt-4"
      claude: "claude-sonnet-4.6"
      openai: "gpt-4-turbo"
      google: "gemini-1-5-pro"
      meta: "llama-3-70b"
    description: "Analysis & planning specialist..."
  
  # ... more roles

provider_features:
  copilot:
    name: "GitHub Copilot"
    thinking: false
    structured_output: true
    max_tokens: 4096
    cost_tier: "premium"
  
  claude:
    name: "Claude (Anthropic)"
    thinking: true
    structured_output: true
    max_tokens: 200000
    cost_tier: "premium"
  
  # ... more providers
```

**Scope of models.yaml:**
- Defines role → model mappings for all providers
- Specifies capability deltas (thinking, structured output, context window)
- Documents effort levels for cost tracking
- Single source for all model-related metadata

**What NOT in models.yaml:**
- Provider credentials/keys (use .env)
- User-specific overrides (use environment variables)
- Runtime model selection logic (use model resolver layer)

### 2. Format Conversion Strategy

**Problem:** Inconsistent model name formats across codebase

**Formats in use:**
1. **Canonical format** (models.yaml keys): `claude-haiku`, `claude-sonnet`, `claude-opus`
2. **Agentic-engineers format** (source agents): `claude-haiku-4.5`, `claude-sonnet-4.6`, `claude-opus-4.7`
3. **SPEC.md format** (documentation): `claude-haiku-4-5` (dashes instead of dots)
4. **Copilot CLI format** (actual usage): `claude-haiku-4.5` (same as agentic-engineers)

**Conversion Mapping**

| Context | Input Format | Resolution | Output Format | Example |
|---------|--------------|-----------|--------------|---------|
| Agent frontmatter | Canonical role | ModelResolver | Full version | `claude-haiku-4.5` |
| Copilot CLI | Canonical role | Provider override | Provider-specific | `gpt-4o-mini` |
| Documentation | Role name | ModelResolver | Full version | `claude-haiku-4.5` |
| Env override | Version string | Direct use | As provided | `claude-opus-4.7` |

**Conversion Flow**

```
INPUT: Role name (e.g., "engineer")
  ↓
[1] Load models.yaml
  ↓
[2] Get role config (role_models[role])
  ↓
[3] Check provider context (PROVIDER env var)
  ↓
[4] Get provider-specific model OR canonical
  ↓
[5] Return full model name: "claude-haiku-4.5"
```

**Implementation: ModelResolver Class**

Location: `src/models/resolver.py` (new file)

```python
class ModelResolver:
    """Resolves role names to provider-specific model names"""
    
    def __init__(self, models_yaml_path: str = None):
        """Load models.yaml (auto-detect if not provided)"""
        
    def resolve(self, role: str, provider: str = None) -> str:
        """Get model name for role in context of provider"""
        # Returns "claude-haiku-4.5" or provider-specific equivalent
        
    def resolve_with_env_override(self, role: str) -> str:
        """Resolve with environment variable support"""
        # Check AGENT_MODEL_OVERRIDE, MODEL_OVERRIDE env vars
        
    def get_canonical(self, role: str) -> str:
        """Get canonical model for role (provider-independent)"""
        
    def get_effort(self, role: str) -> str:
        """Get effort level for cost tracking"""
        
    def get_provider_specific(self, role: str, provider: str) -> str:
        """Get provider-specific model name"""
        
    def validate(self, role: str) -> bool:
        """Check if role exists in registry"""
        
    def get_capability_deltas(self, role: str, provider: str) -> List[str]:
        """List capability gaps for this role on this provider"""
```

### 3. Role → Model Mapping

**Normalization Rules**

All role names follow kebab-case convention:
- Source agents use kebab-case filenames: `engineer.md`, `senior-engineer.md`
- models.yaml uses snake_case keys: `engineer`, `senior_engineer`
- Internal mapping handles conversion: `senior-engineer` → `senior_engineer`

**Mapping Table (from models.yaml)**

| Role | Canonical | Effort | Thinking | Agent Files |
|------|-----------|--------|----------|-------------|
| `engineer` | claude-haiku | high | false | engineer.md |
| `senior_engineer` | claude-sonnet | high | true | senior-engineer.md |
| `quality_engineer` | claude-sonnet | medium | true | quality-engineer.md |
| `lead_engineer` | claude-sonnet | high | true | lead-engineer.md |
| `security_engineer` | claude-opus | max | true | security-engineer.md |
| `principal_engineer` | claude-opus | high | true | principal-engineer.md |
| `model_engineer` | claude-haiku | medium | false | model-engineer.md |
| `general_orchestrator` | claude-haiku | low | false | orchestrator.md |
| `orchestrator` | claude-haiku | low | false | orchestrator.md (alias) |
| `metrics` | claude-haiku | low | false | metrics.md |
| `testing` | claude-haiku | low | false | testing.md |
| `spec_engineer` | claude-sonnet | high | true | spec-engineer.md |
| `healing_engineer` | claude-sonnet | high | true | healing-engineer.md |
| `spec_engineer_orchestrator` | claude-sonnet | high | true | spec-engineer-orchestrator.md |

**Validation Rules**
- Every agent file in src/agents/ must map to a role in models.yaml
- Every role in models.yaml should have at least one agent file
- Model references must follow version format: `provider-family-version` (e.g., claude-opus-4.7)

### 4. Environment-Specific Overrides

**Scenario 1: Testing Different Models**

User wants to test whether Sonnet would work for Engineer role without changing source.

```bash
export AGENT_MODEL_OVERRIDE_ENGINEER=claude-sonnet-4.6
# Agent system will use claude-sonnet-4.6 instead of claude-haiku-4.5
```

**Scenario 2: Cost-Saving Mode**

Downgrade all agents to cheaper models temporarily:

```bash
export MODEL_TIER=haiku
# All agents use haiku variant, even if originally assigned Sonnet/Opus
```

**Scenario 3: Provider-Specific Override**

Use Copilot models (GPT-4) instead of Claude:

```bash
export PREFERRED_PROVIDER=copilot
# All agents use provider-specific models from models.yaml
```

**Scenario 4: Session-Level Override**

From USAGE-BUDGET-MANAGER.md, observed pattern:

```yaml
session_model_override: "haiku"  # Temporarily use Haiku instead of Sonnet
```

Agent system should respect this at runtime.

**Override Resolution Order (Precedence)**

1. **Runtime AGENT_MODEL_OVERRIDE_{ROLE}** - Highest priority
2. **Runtime MODEL_TIER** - Apply tier fallback
3. **PREFERRED_PROVIDER** - Use provider variant
4. **Session model_override** - DELEGATE-level override
5. **models.yaml provider-specific** - Provider config
6. **models.yaml canonical** - Default

### 5. Fallback & Default Strategies

**Fallback Scenario 1: Unknown Provider**

```python
role = "engineer"
provider = "unknown_llm_vendor"

# Get models.yaml entry for engineer
config = models['engineer']

# Provider not in config['providers']?
# → Fall back to canonical: "claude-haiku"
# → User must add provider mapping or override
model = config.get('providers', {}).get(provider, config['canonical'])
```

**Fallback Scenario 2: Capability Gap**

Agent requires thinking mode, but provider doesn't support it:

```python
role = "senior_engineer"  # Requires thinking=true
provider = "copilot"      # Doesn't support thinking
model = "gpt-4"           # Provider mapping

# Detect delta:
deltas = get_capability_deltas(role, provider)
# → "⚠️ This role uses extended thinking but provider doesn't support it"

# Action: Log warning, use model anyway but document limitation
```

**Fallback Scenario 3: Missing Environment Variable**

```bash
# User sets invalid override:
export AGENT_MODEL_OVERRIDE_ENGINEER=unknown-model-1.0

# System behavior:
# 1. Try to validate against known models
# 2. If invalid, log WARNING
# 3. Fall back to models.yaml canonical
# 4. Continue execution
```

**Fallback Scenario 4: No models.yaml Found**

```python
# models.yaml not found
try:
    resolver = ModelResolver("/path/to/models.yaml")
except FileNotFoundError:
    # Fallback to embedded defaults
    resolver = ModelResolver.from_defaults()
    logger.warning("Using embedded model defaults, not canonical")
```

**Default Values**

If models.yaml is unavailable or incomplete:

```python
FALLBACK_DEFAULTS = {
    'engineer': 'claude-haiku-4.5',
    'senior_engineer': 'claude-sonnet-4.6',
    'quality_engineer': 'claude-sonnet-4.6',
    'lead_engineer': 'claude-sonnet-4.6',
    'security_engineer': 'claude-opus-4.7',
    'principal_engineer': 'claude-opus-4.7',
    'model_engineer': 'claude-haiku-4.5',
    'orchestrator': 'claude-haiku-4.5',
    'metrics': 'claude-haiku-4.5',
    'testing': 'claude-haiku-4.5',
    'spec_engineer': 'claude-sonnet-4.6',
    'healing_engineer': 'claude-sonnet-4.6',
    'spec_engineer_orchestrator': 'claude-sonnet-4.6',
}
```

---

## Integration Points

### 1. Agent Frontmatter (src/agents/*.md)

**Before:**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks...
model: claude-haiku-4.5  # ← Hard-coded
---
```

**After:**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks...
role: engineer  # ← Reference to models.yaml role
---
```

**Processing:**
- Renderer reads `role: engineer`
- Looks up in models.yaml → canonical model = "claude-haiku"
- Resolves to full name: "claude-haiku-4.5"
- Inserts resolved value into frontmatter during rendering

### 2. Copilot CLI Agent Rendering

**Pipeline:**
```
src/agents/engineer.md (role: engineer)
  ↓
[ModelResolver.resolve(role="engineer", provider="copilot")]
  ↓
Get models.yaml['engineer']['providers']['copilot'] = "gpt-4o-mini"
  ↓
~/.copilot/agents/engineer.agent.md (model: gpt-4o-mini)
```

**Implementation:**
- Update render-copilot-agents.py to use ModelResolver
- Replace hardcoded model with: `resolver.resolve(role, provider="copilot")`

### 3. Documentation Rendering

**docs/SPEC.md Model References**

**Before:**
```markdown
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 |
```

**After (Generated from models.yaml):**
```markdown
| **Orchestrator** | claude-haiku-4.5 | low | $0.03 |
```

**Implementation:**
- Create doc generator that reads models.yaml
- Renders tables, lists, and references dynamically
- Eliminates hard-coded model strings in documentation

### 4. Agent README

**src/agents/README.md**

**Before:**
```markdown
model: claude-haiku-4.5 | claude-sonnet-4.6 | claude-opus-4.7
```

**After (Generated from models.yaml):**
```markdown
model: Resolved from models.yaml role mapping
```

With link to models.yaml for current truth.

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Task 1.1: Create ModelResolver Class**
- Location: `src/models/resolver.py`
- Implement core resolution logic
- Add unit tests (test_model_resolver.py)
- Time: 2 hours
- Dependencies: None

**Task 1.2: Add Environment Override Support**
- Extend ModelResolver with env var checking
- Implement override precedence logic
- Document override scenarios
- Time: 1.5 hours
- Dependencies: Task 1.1

**Task 1.3: Validate and Enhance models.yaml**
- Audit current models.yaml against agent roles
- Add missing entries if any
- Add validation schema (JSON Schema file)
- Time: 1 hour
- Dependencies: None

**Deliverable:** models/resolver.py with tests, enhanced models.yaml, validation schema

### Phase 2: Agent Frontmatter Refactoring (Week 1-2)

**Task 2.1: Update All Agent Frontmatter**
- Convert `model: claude-X` to `role: X` in all 13 agent files
- Add validation step to ensure role exists in models.yaml
- Time: 1.5 hours
- Dependencies: Task 1.3

**Task 2.2: Update Render Pipeline**
- Modify render-copilot-agents.py to use ModelResolver
- Update render/main.py (if used) to leverage resolver
- Test rendering with ModelResolver
- Time: 3 hours
- Dependencies: Task 1.1, 2.1

**Deliverable:** Updated src/agents/*.md with role references, working render pipeline

### Phase 3: Copilot CLI Rendering (Week 2)

**Task 3.1: Integrate Provider-Specific Rendering**
- Update render-copilot-agents.py to:
  - Read role from agent frontmatter
  - Resolve to copilot provider model
  - Inject into frontmatter
- Verify ~/.copilot/agents/ updates correctly
- Time: 2 hours
- Dependencies: Task 2.2

**Task 3.2: Test Provider Consistency**
- Verify claude agents use claude models
- Verify copilot agents use GPT models
- Test fallback when provider not in models.yaml
- Time: 1.5 hours
- Dependencies: Task 3.1

**Deliverable:** Provider-aware agent rendering working end-to-end

### Phase 4: Documentation Cleanup (Week 2-3)

**Task 4.1: Create Doc Generation Script**
- Create `render/doc_generator.py`
- Reads models.yaml
- Generates model reference tables
- Time: 2 hours
- Dependencies: Task 1.1

**Task 4.2: Update docs/SPEC.md**
- Remove hard-coded model references
- Use generated tables from models.yaml
- Update format to use dot notation consistently
- Time: 1.5 hours
- Dependencies: Task 4.1

**Task 4.3: Update src/agents/README.md**
- Reference models.yaml for current model assignments
- Add section explaining role → model mapping
- Link to models.yaml for canonical truth
- Time: 1 hour
- Dependencies: Task 1.1

**Deliverable:** Auto-generated documentation, consistent model formatting

### Phase 5: Testing & Validation (Week 3)

**Task 5.1: Integration Tests**
- Test full pipeline: role → model resolution → rendering
- Test environment overrides
- Test fallback scenarios
- Time: 3 hours
- Dependencies: All Phase 1-4 tasks

**Task 5.2: Validation Script**
- Create `src/models/validate.py`
- Checks:
  - All agent files have valid roles
  - All roles in models.yaml are documented
  - No hard-coded models in source files
  - Format consistency (dots vs dashes)
- Run in CI/CD
- Time: 2 hours
- Dependencies: Task 1.3

**Task 5.3: Update make verify**
- Add model validation to Makefile
- Include in CI/CD pipeline
- Time: 1 hour
- Dependencies: Task 5.2

**Deliverable:** Passing integration tests, CI/CD validation

### Phase 6: Operational Documentation (Week 3)

**Task 6.1: Create Model Management Guide**
- How to add a new role
- How to set environment overrides
- How to verify model assignments
- Troubleshooting guide
- Location: `docs/model-management.md`
- Time: 2 hours
- Dependencies: All previous phases

**Task 6.2: Update INSTALL.md**
- Add section on environment variable options
- Document MODEL_TIER, PREFERRED_PROVIDER, overrides
- Time: 1 hour
- Dependencies: Task 6.1

**Deliverable:** Comprehensive model management documentation

### Phase 7: Deprecation & Cleanup (Week 4)

**Task 7.1: Deprecate Hard-Coded Models**
- Mark old files/patterns as deprecated
- Add migration notes in comments
- Time: 1 hour
- Dependencies: All previous phases

**Task 7.2: Final Audit**
- Grep codebase for remaining hard-coded models
- Ensure zero duplication
- Document any exceptions
- Time: 1 hour
- Dependencies: Task 7.1

**Deliverable:** Clean codebase with zero model duplication

---

## Files to Create/Modify

### New Files

```
src/models/
├── resolver.py           # ModelResolver class
├── defaults.py           # Fallback defaults
├── validate.py           # Validation script
└── __init__.py

tests/
├── test_model_resolver.py
├── test_provider_resolution.py
└── test_env_overrides.py

render/
├── doc_generator.py      # Documentation generator

docs/
├── architecture-model-centralization.md (this file)
└── model-management.md   # Operational guide
```

### Modified Files

```
src/agents/
├── engineer.md           # role: engineer (not model:)
├── senior-engineer.md    # role: senior_engineer
├── quality-engineer.md   # role: quality_engineer
├── lead-engineer.md      # role: lead_engineer
├── security-engineer.md  # role: security_engineer
├── principal-engineer.md # role: principal_engineer
├── model-engineer.md     # role: model_engineer
├── orchestrator.md       # role: general_orchestrator
├── metrics.md            # role: metrics
├── testing.md            # role: testing
├── spec-engineer.md      # role: spec_engineer
├── healing-engineer.md   # role: healing_engineer
└── spec-engineer-orchestrator.md # role: spec_engineer_orchestrator

models.yaml              # Enhanced with validation schema reference
docs/SPEC.md            # Generated from models.yaml
docs/INSTALL.md         # Add environment variable section
renderer/scripts/
├── render-copilot-agents.py  # Use ModelResolver
└── render-copilot-agents.sh  # Updated if needed

Makefile                 # Add model validation targets
```

---

## Technical Specifications

### ModelResolver API

```python
class ModelResolver:
    """Centralized model name resolution"""
    
    def __init__(self, models_yaml: str = None, fallback_to_defaults: bool = True):
        """
        Initialize resolver from models.yaml
        
        Args:
            models_yaml: Path to models.yaml file
            fallback_to_defaults: Use embedded defaults if file not found
        """
        
    def resolve(self, role: str, provider: str = None, override: str = None) -> str:
        """
        Resolve role to model name
        
        Args:
            role: Role name (e.g., 'engineer', 'senior_engineer')
            provider: Provider context (e.g., 'copilot', 'claude')
            override: Explicit override (highest precedence)
            
        Returns:
            Model name (e.g., 'claude-haiku-4.5' or provider-specific)
            
        Raises:
            ValueError: If role not found and fallback_to_defaults=False
        """
        
    def resolve_with_env(self, role: str, provider: str = None) -> str:
        """
        Resolve with environment variable precedence
        
        Checks (in order):
        1. AGENT_MODEL_OVERRIDE_{ROLE}
        2. MODEL_TIER (overrides provider with tier default)
        3. PREFERRED_PROVIDER (uses provider-specific model)
        4. models.yaml provider mapping
        5. models.yaml canonical
        """
        
    def get_capability_deltas(self, role: str, provider: str) -> List[str]:
        """Get list of capability gaps for this role on this provider"""
        
    def validate_all(self) -> ValidationResult:
        """Validate entire registry for consistency"""
        
    @staticmethod
    def from_defaults() -> ModelResolver:
        """Create resolver with embedded defaults (no file needed)"""
```

### Environment Variables

```bash
# Override specific agent model
AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7

# Override all agents to use specific tier
MODEL_TIER=haiku|sonnet|opus

# Use provider-specific models instead of canonical
PREFERRED_PROVIDER=copilot|claude|openai|google|meta

# Enable debug logging for resolution
MODEL_RESOLVER_DEBUG=1

# Path to custom models.yaml
MODELS_REGISTRY_PATH=/path/to/models.yaml
```

### Validation Schema

Create `src/models/schema.json` (JSON Schema):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "role_models": {
      "type": "object",
      "patternProperties": {
        "^[a-z_]+$": {
          "type": "object",
          "required": ["canonical", "thinking", "effort", "providers", "description"],
          "properties": {
            "canonical": {"type": "string", "pattern": "^[a-z]+-[a-z]+$"},
            "thinking": {"type": "boolean"},
            "effort": {"enum": ["low", "medium", "high", "max"]},
            "providers": {
              "type": "object",
              "minProperties": 1
            },
            "description": {"type": "string"}
          }
        }
      }
    },
    "provider_features": {
      "type": "object",
      "patternProperties": {
        "^[a-z_]+$": {
          "type": "object",
          "required": ["name", "thinking", "structured_output", "max_tokens"],
          "properties": {
            "name": {"type": "string"},
            "thinking": {"type": "boolean"},
            "structured_output": {"type": "boolean"},
            "max_tokens": {"type": "number", "minimum": 1},
            "cost_tier": {"enum": ["budget", "standard", "premium"]}
          }
        }
      }
    }
  },
  "required": ["role_models", "provider_features"]
}
```

---

## Migration Path

### Step 1: Dual-Mode Support (Temporary)

During transition, support both old and new format:

```python
def extract_model_from_agent(frontmatter):
    # Check new format first
    if 'role' in frontmatter:
        role = frontmatter['role']
        return resolver.resolve(role)
    
    # Fall back to old format
    if 'model' in frontmatter:
        return frontmatter['model']
    
    raise ValueError("No role or model specified")
```

### Step 2: Gradual Migration

1. Add role field to each agent file (keep model for now)
2. Update render pipeline to use role if present
3. Validate all agents have valid roles
4. Remove model field from all agent files

### Step 3: Cleanup

1. Update all references to use role-based resolution
2. Run validation to ensure no hard-coded models remain
3. Mark old patterns as deprecated

---

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| models.yaml becomes out of sync | Agent assignments break | Validation script in CI/CD, clear ownership |
| Hard-coded models persist | Defeats centralization goal | Grep checks in pre-commit, linting rules |
| Provider not in models.yaml | Fallback to canonical, but different behavior | Explicit error message, require override |
| Override precedence confusion | Wrong model used | Clear documentation, debug logging |
| Migration breaks rendering | Copilot agents fail to deploy | Dual-mode support during transition |

---

## Success Metrics

### Quantitative
- [ ] Zero hard-coded model names in source code (verified by grep)
- [ ] 100% agent files have valid role references in models.yaml
- [ ] All CI/CD validation tests passing
- [ ] Documentation auto-generated from single source (verified by script)

### Qualitative
- [ ] Easy to add new roles (< 5 minutes)
- [ ] Easy to test different models (single env var)
- [ ] Clear understanding of model assignments across team
- [ ] Reduced maintenance burden for model updates

---

## References

- **models.yaml** — Current model registry (source of truth)
- **src/agents/*.md** — Agent definitions to be refactored
- **docs/SPEC.md** — Specification with model references
- **render/main.py** — Existing ModelResolver implementation
- **USAGE-BUDGET-MANAGER.md** — Documents session_model_override pattern

---

## Next Steps

1. **Approval:** Review architecture with team
2. **Planning:** Create detailed implementation tasks
3. **Execution:** Follow Phase 1-7 roadmap
4. **Validation:** Run CI/CD checks at each phase
5. **Documentation:** Update guides and runbooks
6. **Deployment:** Render agents and verify Copilot CLI compatibility

