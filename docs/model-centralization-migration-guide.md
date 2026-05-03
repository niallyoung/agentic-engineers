# Model Centralization Migration Guide

## Overview

This guide helps you migrate from hardcoded model names scattered across the codebase to the centralized `models.yaml` configuration. The migration uses a **dual-mode approach** that allows you to transition gradually without breaking existing code.

**Timeline:** Phase 6 Implementation
**Effort:** 2-4 hours for complete migration
**Risk:** Low (backward compatible during migration)

---

## Current State: Hardcoded Models

### Where Models Are Currently Hardcoded

#### 1. Agent Definition Files (`src/agents/*.md`)

**Current format:**
```yaml
---
name: Engineer
description: Execution specialist for well-scoped implementation tasks
model: claude-haiku-4.5  # ← Hardcoded
---
```

**Files affected:**
- `src/agents/engineer.md`
- `src/agents/senior-engineer.md`
- `src/agents/quality-engineer.md`
- `src/agents/lead-engineer.md`
- `src/agents/security-engineer.md`
- `src/agents/principal-engineer.md`
- `src/agents/model-engineer.md`
- `src/agents/orchestrator.md`
- `src/agents/metrics.md`
- `src/agents/testing.md`
- `src/agents/spec-engineer.md`
- `src/agents/healing-engineer.md`
- `src/agents/spec-engineer-orchestrator.md`

#### 2. Documentation (`docs/SPEC.md`)

**Current format:**
```markdown
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 |
| **Engineer** | claude-haiku-4-5 | high | $0.03 |
```

Model names hardcoded in multiple tables and references.

#### 3. Agent README (`src/agents/README.md`)

**Current format:**
```markdown
| **Haiku** | 1x | Well-scoped work | engineer, orchestrator, metrics, testing |
```

Implicit model mappings without explicit role references.

#### 4. Copilot CLI Agents (`~/.copilot/agents/*.agent.md`)

**Current format:**
```yaml
---
name: Engineer
model: claude-haiku-4.5  # ← Generated, same as source
---
```

Generated from source files by render pipeline.

---

## Migration Path

### Phase 1: Add Role References (Dual-Mode Setup)

In this phase, we add the `role` field to agent files while keeping `model` for compatibility.

#### Step 1.1: Update Agent Frontmatter

**Before:**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks
model: claude-haiku-4.5
---
```

**After:**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks
role: engineer
model: claude-haiku-4.5  # Keep for now (fallback)
---
```

**Changes:**
- Add `role: {role_name}` field (use snake_case)
- Keep existing `model:` field (dual-mode)

**Updated agent files:**

| Agent File | Role Name |
|------------|-----------|
| `engineer.md` | `engineer` |
| `senior-engineer.md` | `senior_engineer` |
| `quality-engineer.md` | `quality_engineer` |
| `lead-engineer.md` | `lead_engineer` |
| `security-engineer.md` | `security_engineer` |
| `principal-engineer.md` | `principal_engineer` |
| `model-engineer.md` | `model_engineer` |
| `orchestrator.md` | `general_orchestrator` |
| `metrics.md` | `metrics` |
| `testing.md` | `testing` |
| `spec-engineer.md` | `spec_engineer` |
| `healing-engineer.md` | `healing_engineer` |
| `spec-engineer-orchestrator.md` | `spec_engineer_orchestrator` |

#### Step 1.2: Verify Roles Exist in models.yaml

Check that all roles are defined in `models.yaml`:

```bash
python3 << 'EOF'
from orchestration.agents.model_resolver import ModelResolver

resolver = ModelResolver("models.yaml")
roles = ["engineer", "senior_engineer", "quality_engineer", "lead_engineer",
         "security_engineer", "principal_engineer", "model_engineer",
         "general_orchestrator", "metrics", "testing", "spec_engineer",
         "healing_engineer", "spec_engineer_orchestrator"]

for role in roles:
    if resolver.validate(role):
        print(f"✓ {role}")
    else:
        print(f"✗ {role} - MISSING FROM models.yaml")
EOF
```

All roles should be present.

### Phase 2: Update Render Pipeline (Dual-Mode Resolution)

In this phase, the render pipeline uses the new `role` field if present, falling back to `model` if not.

#### Step 2.1: Update render-copilot-agents.py

**Before:**
```python
def extract_model(frontmatter):
    return frontmatter['model']
```

**After (Dual-Mode):**
```python
from orchestration.agents.model_resolver import ModelResolver

def extract_model(frontmatter, provider=None):
    resolver = ModelResolver("models.yaml")
    
    # Check new format first
    if 'role' in frontmatter:
        role = frontmatter['role']
        return resolver.resolve(role, provider=provider)
    
    # Fall back to old format
    if 'model' in frontmatter:
        return frontmatter['model']
    
    raise ValueError("Agent must have 'role' or 'model' field")
```

#### Step 2.2: Update Copilot Rendering

When rendering for Copilot CLI, use provider-specific models:

```python
# In render-copilot-agents.py
model = extract_model(agent_yaml, provider='copilot')
# Instead of plain model name, now uses:
# - Role-based lookup if 'role' present
# - Provider-specific mapping from models.yaml
# - Falls back to hardcoded model if 'role' not present
```

#### Step 2.3: Test Rendering

```bash
# Run render pipeline
python3 renderer/scripts/render-copilot-agents.py

# Verify agents were updated
ls ~/.copilot/agents/ | wc -l  # Should have all agents
head -20 ~/.copilot/agents/engineer.agent.md  # Check model field
```

### Phase 3: Update Documentation (Clean Up Hardcoding)

In this phase, we remove hardcoded model references from documentation.

#### Step 3.1: Create Documentation Generator

Create `render/doc_generator.py`:

```python
from orchestration.agents.model_resolver import ModelResolver
from pathlib import Path

def generate_agent_table():
    """Generate agent specs table from models.yaml."""
    resolver = ModelResolver("models.yaml")
    
    rows = []
    for role in sorted(resolver.list_all_roles()):
        canonical = resolver.get_canonical(role)
        effort = resolver.get_effort(role)
        # ... format as markdown table row
        rows.append((role, canonical, effort))
    
    return "| Role | Model | Effort |\n" + "\n".join(rows)

def generate_provider_matrix():
    """Generate provider model matrix from models.yaml."""
    resolver = ModelResolver("models.yaml")
    # ... generate cross-provider table
    pass
```

#### Step 3.2: Update docs/SPEC.md

Replace hardcoded tables with generated content:

**Before:**
```markdown
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 |
| **Engineer** | claude-haiku-4-5 | high | $0.03 |
| **Senior Engineer** | claude-sonnet-4-6 | high | $0.10 |
```

**After (Auto-Generated):**
```markdown
<!-- AUTO-GENERATED FROM models.yaml -->
<!-- Run: python3 render/doc_generator.py -->

| **Role** | **Model** | **Effort** |
|----------|-----------|-----------|
| orchestrator | claude-haiku | low |
| engineer | claude-haiku | high |
| senior_engineer | claude-sonnet | high |
```

Add comment that tables are auto-generated.

#### Step 3.3: Update src/agents/README.md

**Before:**
```markdown
| Haiku | 1x | Well-scoped work | engineer, orchestrator, metrics, testing |
```

**After:**
```markdown
See `models.yaml` for current model assignments and `docs/model-configuration-guide.md` for usage.

| Model | Roles |
|-------|-------|
| claude-haiku | engineer, orchestrator, metrics, testing |
| claude-sonnet | senior_engineer, quality_engineer, ... |
| claude-opus | security_engineer, principal_engineer |
```

### Phase 4: Validation and Testing

#### Step 4.1: Create Validation Script

Create `orchestration/agents/validate_models.py`:

```python
#!/usr/bin/env python3
from orchestration.agents.model_resolver import ModelResolver
from pathlib import Path
import sys

def validate_agents():
    """Validate all agent files have valid roles in models.yaml."""
    resolver = ModelResolver("models.yaml")
    
    errors = []
    agents_dir = Path("src/agents")
    
    for agent_file in agents_dir.glob("*.md"):
        # Parse frontmatter
        role = extract_role_from_agent(agent_file)
        
        if not role:
            errors.append(f"{agent_file}: Missing 'role' field")
        elif not resolver.validate(role):
            errors.append(f"{agent_file}: Invalid role '{role}'")
    
    return errors

def validate_hardcoded_models():
    """Check for remaining hardcoded model strings in source."""
    hardcoded_patterns = [
        'claude-haiku-',
        'claude-sonnet-',
        'claude-opus-',
        'gpt-4',
        'gemini-',
        'llama-3-'
    ]
    
    # Search for hardcoded models in non-models.yaml files
    # Report any found
    pass

if __name__ == "__main__":
    errors = validate_agents()
    
    if errors:
        print("Validation FAILED:")
        for error in errors:
            print(f"  ✗ {error}")
        sys.exit(1)
    else:
        print("✓ All agents have valid roles")
        sys.exit(0)
```

#### Step 4.2: Add to Makefile

```makefile
verify-models:
	python3 orchestration/agents/validate_models.py

verify: verify-models
```

Run validation:

```bash
make verify-models
```

#### Step 4.3: Test End-to-End

```bash
# Test Python API
python3 << 'EOF'
from orchestration.agents.model_resolver import ModelResolver

resolver = ModelResolver("models.yaml")

# Test basic resolution
assert resolver.resolve("engineer") == "claude-haiku"
assert resolver.resolve("senior_engineer") == "claude-sonnet"

# Test provider resolution
assert "gpt" in resolver.resolve("engineer", provider="copilot")
assert "claude" in resolver.resolve("engineer", provider="claude")

# Test environment overrides
import os
os.environ["AGENT_MODEL_OVERRIDE_ENGINEER"] = "gpt-4-turbo"
assert resolver.resolve_with_env("engineer") == "gpt-4-turbo"

print("✓ All tests passed")
EOF
```

### Phase 5: Remove Hardcoded Models

Once all validation passes, remove the `model` field from agent files.

#### Step 5.1: Clean Agent Frontmatter

**Before (Dual-Mode):**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks
role: engineer
model: claude-haiku-4.5  # ← Remove this
---
```

**After (Clean):**
```yaml
---
name: Engineer
description: Executes well-scoped implementation tasks
role: engineer
---
```

**Update all 13 agent files.**

#### Step 5.2: Update Render Pipeline (Clean Mode)

**Before (Dual-Mode):**
```python
def extract_model(frontmatter, provider=None):
    if 'role' in frontmatter:
        return resolver.resolve(frontmatter['role'], provider=provider)
    if 'model' in frontmatter:
        return frontmatter['model']
    raise ValueError("No role or model")
```

**After (Clean Mode):**
```python
def extract_model(frontmatter, provider=None):
    if 'role' not in frontmatter:
        raise ValueError("Agent frontmatter must have 'role' field")
    return resolver.resolve(frontmatter['role'], provider=provider)
```

#### Step 5.3: Remove Hardcoded References from Code

Search for remaining hardcoded models:

```bash
# Find remaining hardcoded models in source (should be minimal)
grep -r "claude-haiku\|claude-sonnet\|claude-opus\|gpt-4\|gpt-4o" \
  src/ orchestration/ --include="*.py" --include="*.md" \
  | grep -v "models.yaml" \
  | grep -v "model_resolver.py"
```

Remove any found, replacing with ModelResolver usage.

#### Step 5.4: Final Validation

```bash
make verify-models  # Should pass with no errors

# Run full test suite
python3 -m pytest orchestration/agents/test_model_resolver.py -v

# Verify rendering works
python3 renderer/scripts/render-copilot-agents.py
ls ~/.copilot/agents/ | wc -l  # All agents present
```

---

## Migration Checklist

### Phase 1: Add Role References
- [ ] Add `role:` field to all 13 agent files
- [ ] Verify roles match models.yaml keys
- [ ] Keep `model:` field for fallback
- [ ] Commit changes

### Phase 2: Update Render Pipeline
- [ ] Implement dual-mode `extract_model()` in renderer
- [ ] Update render-copilot-agents.py to use ModelResolver
- [ ] Test rendering produces correct models
- [ ] Verify provider-specific models correct
- [ ] Commit changes

### Phase 3: Update Documentation
- [ ] Create render/doc_generator.py
- [ ] Generate agent specification tables
- [ ] Update docs/SPEC.md with generated content
- [ ] Update src/agents/README.md
- [ ] Commit changes

### Phase 4: Validation and Testing
- [ ] Create validate_models.py script
- [ ] Add verify-models target to Makefile
- [ ] Run all validation checks
- [ ] Pass test suite
- [ ] Test environment overrides work
- [ ] Commit changes

### Phase 5: Clean Up Hardcoded Models
- [ ] Remove `model:` field from all agent files
- [ ] Update render pipeline to strict mode
- [ ] Remove remaining hardcoded model references
- [ ] Final validation: make verify-models
- [ ] Final testing
- [ ] Commit changes

---

## Rollback Plan

If issues arise during migration:

### Rollback Point 1 (After Phase 1)
If agent updates cause problems, you can revert the `role:` field additions without affecting rendering. The `model:` field is still being used.

```bash
git revert <phase1_commit>
```

### Rollback Point 2 (After Phase 2)
If rendering breaks, revert to simple `model:` extraction:

```bash
git revert <phase2_commit>
# Rendering still works using hardcoded model field
```

### Rollback Point 3 (After Phase 3)
If documentation generation fails, revert to hardcoded content:

```bash
git revert <phase3_commit>
```

### Full Rollback
Return to pre-migration state:

```bash
git checkout <pre_migration_commit>
```

---

## Testing During Migration

### Test Agent Resolution
```python
from orchestration.agents.model_resolver import ModelResolver

resolver = ModelResolver("models.yaml")
for role in resolver.list_all_roles():
    model = resolver.resolve(role)
    print(f"{role} → {model}")
```

### Test Provider Resolution
```python
for provider in ["copilot", "claude", "openai", "google", "meta"]:
    model = resolver.resolve("engineer", provider=provider)
    print(f"engineer ({provider}) → {model}")
```

### Test Environment Overrides
```bash
export AGENT_MODEL_OVERRIDE_ENGINEER=gpt-4-turbo
export MODEL_TIER=haiku
export PREFERRED_PROVIDER=copilot

python3 << 'EOF'
from orchestration.agents.model_resolver import ModelResolver
resolver = ModelResolver("models.yaml")
print(resolver.resolve_with_env("engineer"))
EOF
```

### Test Rendering
```bash
python3 renderer/scripts/render-copilot-agents.py
head -30 ~/.copilot/agents/engineer.agent.md
```

---

## Common Issues and Solutions

### Issue: Role Not Found in models.yaml

**Problem:**
```
ModelNotFoundError: Role 'unknown_role' not found
```

**Solution:**
1. Check spelling (use snake_case)
2. Verify role exists in models.yaml
3. Add missing role if needed

### Issue: Wrong Model Selected After Update

**Problem:**
Agent using old hardcoded model instead of models.yaml version.

**Solution:**
1. Ensure `role:` field is present in agent file
2. Verify role name matches models.yaml key
3. Check ModelResolver loads correct models.yaml
4. Clear Python cache: `find . -type d -name __pycache__ -delete`

### Issue: Rendering Fails

**Problem:**
```
ValueError: Agent must have 'role' or 'model' field
```

**Solution:**
1. Ensure all agent files have `role:` field
2. Check for typos in role names
3. Revert to Phase 1 (both `role:` and `model:` present)

### Issue: Environment Variables Not Respected

**Problem:**
Setting `AGENT_MODEL_OVERRIDE_*` has no effect.

**Solution:**
1. Use `resolve_with_env()` instead of `resolve()`
2. Check environment variable name (uppercase, underscores)
3. Verify `MODEL_RESOLVER_DEBUG=1` shows override being checked
4. Ensure resolver is reloaded after changing environment

---

## Performance Considerations

### ModelResolver Initialization
- **Cold start:** ~10ms (YAML parsing)
- **After first load:** Cached in memory
- **Overhead:** Negligible for most use cases

### Lazy Initialization
For performance-critical paths, initialize once:

```python
# Global or module-level
_resolver = None

def get_resolver():
    global _resolver
    if not _resolver:
        _resolver = ModelResolver("models.yaml")
    return _resolver

# Use throughout
model = get_resolver().resolve("engineer")
```

### Batch Resolution
For multiple role resolutions:

```python
resolver = ModelResolver("models.yaml")
models = {role: resolver.resolve(role) for role in roles}
```

---

## Timeline Estimate

| Phase | Duration | Risk |
|-------|----------|------|
| Phase 1: Add Role References | 30 min | Low |
| Phase 2: Update Renderer | 1 hour | Low |
| Phase 3: Update Documentation | 1 hour | Low |
| Phase 4: Validation | 30 min | Low |
| Phase 5: Clean Up | 30 min | Low |
| **Total** | **3.5 hours** | **Low** |

---

## See Also

- **[Architecture Design](./architecture-model-centralization.md)** - Full technical specification
- **[Model Configuration Guide](./model-configuration-guide.md)** - How to use models.yaml
- **[ModelResolver API](../orchestration/agents/model_resolver.py)** - Implementation
- **[models.yaml](../models.yaml)** - Single source of truth
