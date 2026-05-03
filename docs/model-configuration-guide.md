# Model Configuration Guide

## Overview

This guide explains how to use `models.yaml` as the single source of truth for agent-to-model mappings. The ModelResolver class provides programmatic access to model configurations with support for environment-specific overrides and fallback strategies.

**See also:**
- [Architecture Design](./architecture-model-centralization.md) - Detailed technical specification
- [Migration Guide](./model-centralization-migration-guide.md) - How to migrate from hardcoded models

---

## Quick Start

### Basic Resolution

The simplest way to resolve a role to a model:

```python
from orchestration.agents.model_resolver import ModelResolver

resolver = ModelResolver("models.yaml")
model = resolver.resolve("engineer")  # Returns "claude-haiku"
```

### Resolution with Provider

Get the provider-specific model:

```python
# For Copilot CLI (GitHub Copilot)
model = resolver.resolve("engineer", provider="copilot")  # Returns "gpt-4o-mini"

# For Claude (Anthropic)
model = resolver.resolve("engineer", provider="claude")   # Returns "claude-haiku-4.5"

# For OpenAI
model = resolver.resolve("engineer", provider="openai")   # Returns "gpt-4o-mini"

# For Google Gemini
model = resolver.resolve("engineer", provider="google")   # Returns "gemini-2.0-flash"

# For Meta Llama
model = resolver.resolve("engineer", provider="meta")     # Returns "llama-3-8b"
```

### Resolution with Environment Variables

Use environment variables to override models without changing code:

```bash
# Override a specific agent's model
export AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7
python3 your_script.py  # engineer role now uses opus

# Use a cheaper model tier for all agents
export MODEL_TIER=haiku
python3 your_script.py  # All agents downgrade to haiku

# Use a specific provider's models
export PREFERRED_PROVIDER=copilot
python3 your_script.py  # All agents use copilot models
```

In Python:

```python
# Automatically checks environment variables in precedence order
model = resolver.resolve_with_env("engineer")
```

---

## Understanding models.yaml

The `models.yaml` file defines all agent-to-model mappings:

```yaml
role_models:
  engineer:
    canonical: "claude-haiku"           # Generic model name
    thinking: false                     # Requires extended thinking?
    effort: "high"                      # Token/cost level: low/medium/high/max
    providers:
      copilot: "gpt-4o-mini"           # Provider-specific models
      claude: "claude-haiku-4.5"
      openai: "gpt-4o-mini"
      google: "gemini-2.0-flash"
      meta: "llama-3-8b"
    description: "Execution specialist - well-scoped, planned work"

  senior_engineer:
    canonical: "claude-sonnet"
    thinking: true                      # Requires extended thinking
    effort: "high"
    providers:
      copilot: "gpt-4"
      claude: "claude-sonnet-4.6"
      openai: "gpt-4-turbo"
      google: "gemini-1-5-pro"
      meta: "llama-3-70b"
    description: "Analysis & planning specialist..."
```

### Role Names

All roles use **snake_case**:
- `engineer`
- `senior_engineer` (not `senior-engineer`)
- `quality_engineer`
- `lead_engineer`
- `security_engineer`
- `principal_engineer`
- `model_engineer`
- `general_orchestrator`
- `metrics`
- `testing`
- `spec_engineer`
- `healing_engineer`
- `spec_engineer_orchestrator`

### Key Fields

| Field | Required | Meaning |
|-------|----------|---------|
| `canonical` | Yes | Generic canonical model (e.g., `claude-haiku`) |
| `thinking` | Yes | Does role require extended thinking mode? |
| `effort` | Yes | Token/cost level: `low`, `medium`, `high`, or `max` |
| `providers` | No | Provider-specific model mappings (if omitted, canonical is used) |
| `description` | Yes | Human-readable description of the role |

---

## Using ModelResolver Programmatically

### Initialization

```python
from orchestration.agents.model_resolver import ModelResolver

# Option 1: Load from explicit path
resolver = ModelResolver("models.yaml")

# Option 2: Auto-detect models.yaml location
resolver = ModelResolver()

# Option 3: Use embedded defaults (no file needed)
resolver = ModelResolver.from_defaults()

# Option 4: Skip fallback if file not found (strict mode)
resolver = ModelResolver(fallback_to_defaults=False)
```

### Core Methods

#### `resolve(role, provider=None, override=None) -> str`

Resolve a role to a model name.

```python
# Basic resolution
model = resolver.resolve("engineer")

# With provider context
model = resolver.resolve("engineer", provider="copilot")

# With explicit override (highest precedence)
model = resolver.resolve("engineer", override="gpt-4-turbo")

# Role name is flexible (kebab-case auto-converts to snake_case)
resolver.resolve("senior-engineer")  # Same as "senior_engineer"
```

#### `resolve_with_env(role, provider=None) -> str`

Resolve with environment variable support.

```python
# Automatically checks:
# 1. AGENT_MODEL_OVERRIDE_{ROLE}
# 2. MODEL_TIER
# 3. PREFERRED_PROVIDER
# 4. models.yaml provider mapping
# 5. models.yaml canonical
model = resolver.resolve_with_env("engineer")
```

#### `get_canonical(role) -> str`

Get the canonical (provider-independent) model.

```python
canonical = resolver.get_canonical("engineer")  # "claude-haiku"
```

#### `get_effort(role) -> str`

Get effort level for cost tracking.

```python
effort = resolver.get_effort("engineer")  # "high"
# Values: "low", "medium", "high", "max"
```

#### `is_thinking_supported(role) -> bool`

Check if role requires extended thinking.

```python
if resolver.is_thinking_supported("senior_engineer"):
    # Use extended thinking model
    pass
```

#### `get_provider_specific(role, provider) -> Optional[str]`

Get provider-specific model for a role.

```python
model = resolver.get_provider_specific("engineer", "copilot")  # "gpt-4o-mini"
```

#### `get_all_providers(role) -> Dict[str, str]`

Get all provider mappings for a role.

```python
providers = resolver.get_all_providers("engineer")
# {
#     "copilot": "gpt-4o-mini",
#     "claude": "claude-haiku-4.5",
#     "openai": "gpt-4o-mini",
#     "google": "gemini-2.0-flash",
#     "meta": "llama-3-8b"
# }
```

#### `validate(role) -> bool`

Check if a role exists.

```python
if resolver.validate("engineer"):
    print("Valid role")
else:
    print("Unknown role")
```

#### `list_all_roles() -> List[str]`

Get all available roles.

```python
roles = resolver.list_all_roles()
# ["engineer", "general_orchestrator", "healing_engineer", ...]
```

#### `list_all_providers() -> List[str]`

Get all supported providers.

```python
providers = resolver.list_all_providers()
# ["claude", "copilot", "google", "meta", "openai"]
```

#### `validate_all() -> Dict`

Validate entire registry.

```python
result = resolver.validate_all()
# {
#     "valid": True,
#     "errors": [],
#     "warnings": [...],
#     "coverage": {
#         "total_roles": 14,
#         "roles_with_all_providers": 10,
#         "roles_missing_providers": [...]
#     }
# }
```

#### `get_capability_deltas(role, provider) -> List[str]`

Get capability gaps for a role on a provider.

```python
deltas = resolver.get_capability_deltas("senior_engineer", "copilot")
# ["Role requires extended thinking but provider 'copilot' doesn't support it"]
```

---

## Environment Variables

### AGENT_MODEL_OVERRIDE_{ROLE}

Override the model for a specific role.

```bash
# Use opus for engineer (normally haiku)
export AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7

# Use haiku for senior_engineer (normally sonnet)
export AGENT_MODEL_OVERRIDE_SENIOR_ENGINEER=claude-haiku-4.5

# Multiple overrides
export AGENT_MODEL_OVERRIDE_ENGINEER=claude-sonnet-4.6
export AGENT_MODEL_OVERRIDE_SECURITY_ENGINEER=gpt-4-turbo
```

**Note:** Role names in environment variables use UPPER_CASE with underscores.

### MODEL_TIER

Temporarily use a specific model tier for all agents.

```bash
# All agents use haiku-class models
export MODEL_TIER=haiku

# All agents use sonnet-class models
export MODEL_TIER=sonnet

# All agents use opus-class models
export MODEL_TIER=opus
```

### PREFERRED_PROVIDER

Use provider-specific models instead of canonical.

```bash
# Use Copilot (GPT) models
export PREFERRED_PROVIDER=copilot

# Use Claude models
export PREFERRED_PROVIDER=claude

# Use OpenAI models
export PREFERRED_PROVIDER=openai

# Valid values: claude, copilot, google, meta, openai
```

### MODEL_RESOLVER_DEBUG

Enable debug logging.

```bash
# Show detailed resolution logs
export MODEL_RESOLVER_DEBUG=1
python3 your_script.py
```

### MODELS_REGISTRY_PATH

Custom path to models.yaml.

```bash
export MODELS_REGISTRY_PATH=/path/to/custom/models.yaml
python3 your_script.py
```

---

## Environment Override Precedence

The resolver checks environment variables in this order:

1. **AGENT_MODEL_OVERRIDE_{ROLE}** (highest priority)
   - Example: `AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7`
   - If set, always used

2. **MODEL_TIER**
   - Example: `MODEL_TIER=haiku`
   - Applies to all agents

3. **PREFERRED_PROVIDER**
   - Example: `PREFERRED_PROVIDER=copilot`
   - Uses provider-specific models from models.yaml

4. **models.yaml provider mapping**
   - Uses specified provider's model if available

5. **models.yaml canonical** (fallback)
   - Default model name

### Example: Precedence in Action

```bash
export AGENT_MODEL_OVERRIDE_ENGINEER=gpt-4-turbo
export MODEL_TIER=haiku
export PREFERRED_PROVIDER=copilot

# Which wins?
# Answer: AGENT_MODEL_OVERRIDE_ENGINEER (gpt-4-turbo)
# Because it's checked first
```

---

## Common Use Cases

### Testing Different Models

Test whether Sonnet would work for Engineer role:

```bash
export AGENT_MODEL_OVERRIDE_ENGINEER=claude-sonnet-4.6
python3 your_script.py
```

### Cost-Saving Mode

Temporarily downgrade all agents to cheaper models:

```bash
export MODEL_TIER=haiku
python3 your_script.py  # All agents use haiku-class models
```

### Using Specific Provider

Force all agents to use OpenAI models:

```bash
export PREFERRED_PROVIDER=openai
python3 your_script.py
```

### Debug Model Resolution

See what model each agent is getting:

```bash
export MODEL_RESOLVER_DEBUG=1
python3 your_script.py
```

### Custom models.yaml

Use a custom models.yaml file:

```bash
export MODELS_REGISTRY_PATH=/path/to/my/models.yaml
python3 your_script.py
```

---

## Adding a New Role

To add a new agent role:

1. **Add entry to models.yaml:**

```yaml
my_new_role:
  canonical: "claude-sonnet"
  thinking: true
  effort: "high"
  providers:
    copilot: "gpt-4"
    claude: "claude-sonnet-4.6"
    openai: "gpt-4-turbo"
    google: "gemini-1-5-pro"
    meta: "llama-3-70b"
  description: "Description of the new role"
```

2. **Use in code:**

```python
resolver = ModelResolver("models.yaml")
model = resolver.resolve("my_new_role")
```

3. **Validate:**

```python
result = resolver.validate_all()
print(result['valid'])  # Should be True if properly added
```

---

## Troubleshooting

### Role Not Found

**Error:**
```
ModelNotFoundError: Role 'unknown_role' not found
```

**Solution:**
- Check role name spelling (use snake_case)
- Verify role exists in models.yaml
- Use `resolver.list_all_roles()` to see available roles

### Provider Not Found

**Problem:** Agent gets canonical model instead of provider-specific.

**Reason:** Provider not defined in models.yaml for that role.

**Solution:**
- Add provider mapping to models.yaml
- Use explicit override: `export AGENT_MODEL_OVERRIDE_ROLE=model-name`
- Check capability deltas: `resolver.get_capability_deltas(role, provider)`

### Wrong Model Selected

**Problem:** Different model than expected.

**Debug:**
```python
# Check what's being resolved
import os
os.environ['MODEL_RESOLVER_DEBUG'] = '1'

resolver = ModelResolver("models.yaml")
model = resolver.resolve_with_env("engineer")
```

**Check precedence:**
1. Is `AGENT_MODEL_OVERRIDE_*` set? (highest priority)
2. Is `MODEL_TIER` set?
3. Is `PREFERRED_PROVIDER` set?
4. Check models.yaml content
5. Check fallback defaults

---

## Best Practices

1. **Always use snake_case role names** internally
2. **Use `resolve_with_env()`** in production (respects environment variables)
3. **Validate roles** before use with `validate(role)`
4. **Check capability deltas** when switching providers
5. **Set `MODEL_RESOLVER_DEBUG=1`** when troubleshooting
6. **Keep models.yaml updated** as models change
7. **Use environment variables** for temporary overrides, not code changes

---

## See Also

- **[Architecture Design](./architecture-model-centralization.md)** - Full technical specification
- **[Migration Guide](./model-centralization-migration-guide.md)** - How to migrate from hardcoded models
- **[models.yaml](../models.yaml)** - Complete model registry
- **[ModelResolver API](../orchestration/agents/model_resolver.py)** - Source code with docstrings
