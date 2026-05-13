---
title: Model Optimization Architecture
type: Architecture Reference
status: APPROVED
created: 2025-05-15
updated: 2026-04-28
---

# Model Optimization Architecture

> **Canonical reference** for model configuration, selection, and optimization.
> Consolidates: ADR-model-centralization, architecture-model-centralization,
> model-centralization-design-summary, model-centralization-migration-guide,
> model-configuration-guide, MODEL-SELECTION-STRATEGY.

---

## 1. Architecture Decision (ADR)

### Status: APPROVED — Implemented

### Problem

Hard-coded model references are scattered across 13+ files:
- `src/agents/*.md` — 13 agent files with `model: claude-haiku-4.5` in frontmatter
- `docs/SPEC.md` — multiple tables with hard-coded model names
- `~/.copilot/agents/` — rendered duplicates of source model names
- No mechanism for environment-specific overrides

**Cost of status quo:** Changing a model requires updates in 3+ locations with risk of inconsistency.

### Decision

Implement a **centralized model naming system**:

1. **Single Source of Truth** — `models.yaml` is the canonical model registry
2. **Role-Based Frontmatter** — agent files reference `role:` not `model:`
3. **ModelResolver class** — resolves role → provider-specific model at build time
4. **Environment Overrides** — `AGENT_MODEL_OVERRIDE_{ROLE}`, `MODEL_TIER`, `PREFERRED_PROVIDER`
5. **Graceful Fallback** — missing provider → canonical; invalid override → canonical + warning

### Success Criteria

- [ ] Zero hard-coded model names in `src/agents/` (grep verified)
- [ ] All agent files reference valid roles in `models.yaml`
- [ ] CI/CD validation passing (`make verify-models`)
- [ ] Documentation generated from single source

---

## 2. Centralized Configuration Architecture

### models.yaml — Single Source of Truth

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
    description: "Execution specialist - well-scoped, planned work"

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
```

### Role → Model Mapping (13 Agents)

| Role | Canonical | Claude | Copilot | Effort |
|------|-----------|--------|---------|--------|
| `engineer` | claude-haiku | claude-haiku-4.5 | gpt-4o-mini | high |
| `senior_engineer` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | high |
| `quality_engineer` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | medium |
| `lead_engineer` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | high |
| `security_engineer` | claude-opus | claude-opus-4.7 | gpt-4o | max |
| `principal_engineer` | claude-opus | claude-opus-4.7 | gpt-4o | high |
| `model_engineer` | claude-haiku | claude-haiku-4.5 | gpt-4o-mini | medium |
| `general_orchestrator` | claude-haiku | claude-haiku-4.5 | gpt-4o-mini | low |
| `metrics` | claude-haiku | claude-haiku-4.5 | gpt-4o-mini | low |
| `testing` | claude-haiku | claude-haiku-4.5 | gpt-4o-mini | low |
| `spec_engineer` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | high |
| `healing_engineer` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | high |
| `spec_engineer_orchestrator` | claude-sonnet | claude-sonnet-4.6 | gpt-4 | high |

### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│  Configuration Layer                                     │
│  models.yaml (13 roles × 5 providers = 65 mappings)    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  Resolution Layer                                        │
│  ModelResolver (orchestration/agents/model_resolver.py) │
│  resolve(role, provider) → model name                   │
│  resolve_with_env(role) → env overrides + model name    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  Rendering Layer                                         │
│  src/agents/*.md (role: engineer)                        │
│       ↓ [render pipeline]                                │
│  ~/.copilot/agents/engineer.agent.md (model: gpt-4o-mini)│
└─────────────────────────────────────────────────────────┘
```

---

## 3. Model Selection Strategy

### Core Principle

**Match model capabilities to task requirements.** Select the smallest model that reliably solves the task, regardless of vendor.

### Model Strength Profiles

#### Claude Haiku 4.5 (`$0.80/$2.40 per 1M tokens`, ~500ms–1s)
**Best for:**
- Structured output parsing (JSON, YAML, test results)
- Numeric analysis and arithmetic (token ratios, percentages, scoring)
- Simple routing and classification
- State management (reading/writing parameters)

**Agent assignments:** Testing, Metrics, Model Engineer, Orchestrator

#### Claude Sonnet 4.6 (`$3/$15 per 1M tokens`, ~2–5s)
**Best for:**
- Multi-step reasoning and planning
- Code generation and refactoring
- Complex problem decomposition
- Trade-off analysis
- Context aggregation from multiple sources

**Agent assignments:** Engineer, Senior Engineer, Quality Engineer, Healing Engineer, Spec Engineer

#### Claude Opus 4.7 (`$15/$45 per 1M tokens`, ~5–10s)
**Best for:**
- Security-critical analysis (zero false negatives required)
- Threat modeling and attack surface analysis
- High-stakes decision support
- Cross-domain reasoning

**Agent assignments:** Security Engineer, Principal Engineer

### Decision Tree

```
Task requirements?
│
├─ "Output structured data (JSON, YAML, counts, percentages)"
│  └─ Try HAIKU first
│     ≥95% success: ✅ STAY HAIKU
│     80–95%: Try SONNET
│     <80%: Escalate to OPUS
│
├─ "Multi-step reasoning, code generation, trade-offs"
│  └─ Use SONNET
│
├─ "Security-critical, zero false negatives required"
│  └─ Use OPUS (non-negotiable)
│
├─ "Fast routing, simple classification"
│  └─ Use HAIKU
│
└─ "Unknown / first time solving this problem"
   └─ Start with SONNET, downgrade after 5–10 runs if data supports
```

### Cost Model

| Task Type | Haiku | Sonnet | Opus | Selection |
|-----------|-------|--------|------|-----------|
| Parsing + Counting | $0.02–0.05 | $0.06–0.15 | — | **Haiku** |
| Numeric Analysis | $0.02–0.06 | $0.09–0.21 | — | **Haiku** |
| Routing | $0.01–0.03 | $0.06–0.15 | — | **Haiku** |
| Code Review | — | $0.09–0.24 | $0.27–0.60 | **Sonnet** |
| Auto-fix Code | — | $0.09–0.24 | $0.27–0.60 | **Sonnet** |
| Security Scanning | — | $0.15–0.45 | $0.18–0.45 | **Opus** |
| Architecture Design | — | $0.15–0.45 | $0.30–0.75 | **Sonnet** |

### Optimization Workflow

**Phase 1 — Validation (Use Sonnet):** Run task 5–10 times, measure success rate, token usage, latency.

**Phase 2 — Cost Optimization:** Downgrade to Haiku if ≥95% success rate. Keep Sonnet if 80–95%. Upgrade to Opus if <80%.

**Phase 3 — Continuous Learning (Model Engineer Agent):** Track PASS/FAIL, update confidence after 20 runs.

---

## 4. Configuration Guide (ModelResolver API)

### Initialization

```python
from orchestration.agents.model_resolver import ModelResolver

resolver = ModelResolver("models.yaml")
```

### Core Methods

```python
# Basic resolution
model = resolver.resolve("engineer")                          # → "claude-haiku"
model = resolver.resolve("engineer", provider="copilot")     # → "gpt-4o-mini"
model = resolver.resolve("engineer", provider="claude")      # → "claude-haiku-4.5"

# Environment variable support
model = resolver.resolve_with_env("engineer")                 # checks overrides first

# Introspection
canonical = resolver.get_canonical("engineer")                # → "claude-haiku"
effort    = resolver.get_effort("engineer")                   # → "high"
thinking  = resolver.is_thinking_supported("senior_engineer") # → True
providers = resolver.get_all_providers("engineer")            # → {copilot: ..., claude: ...}
valid     = resolver.validate("engineer")                     # → True
roles     = resolver.list_all_roles()                         # → [engineer, ...]
```

### Environment Variables

| Variable | Example | Effect |
|----------|---------|--------|
| `AGENT_MODEL_OVERRIDE_{ROLE}` | `AGENT_MODEL_OVERRIDE_ENGINEER=claude-opus-4.7` | Override specific role (highest priority) |
| `MODEL_TIER` | `MODEL_TIER=haiku` | Apply tier to all agents |
| `PREFERRED_PROVIDER` | `PREFERRED_PROVIDER=copilot` | Use provider-specific models globally |
| `MODEL_RESOLVER_DEBUG` | `MODEL_RESOLVER_DEBUG=1` | Enable debug logging |
| `MODELS_REGISTRY_PATH` | `MODELS_REGISTRY_PATH=/custom/models.yaml` | Custom registry path |

**Precedence order (highest → lowest):**
1. `AGENT_MODEL_OVERRIDE_{ROLE}`
2. `MODEL_TIER`
3. `PREFERRED_PROVIDER`
4. `models.yaml` provider mapping
5. `models.yaml` canonical

---

## 5. Migration Guide

### Current → Target State

**Before (hard-coded):**
```yaml
---
name: Engineer
model: claude-haiku-4.5    # ← hard-coded in 3+ locations
---
```

**After (role-based):**
```yaml
---
name: Engineer
role: engineer             # ← resolved at build time from models.yaml
---
```

### Migration Steps

**Phase 1: Add role references (dual-mode)**
```yaml
name: Engineer
role: engineer
model: claude-haiku-4.5    # Keep as fallback during transition
```

**Phase 2: Update render pipeline**
```python
from orchestration.agents.model_resolver import ModelResolver

def extract_model(frontmatter, provider=None):
    resolver = ModelResolver("models.yaml")
    if 'role' in frontmatter:
        return resolver.resolve(frontmatter['role'], provider=provider)
    return frontmatter['model']  # fallback
```

**Phase 3: Remove hard-coded `model:` fields** (after validation passes)

**Phase 4: Validate**
```bash
make verify-models   # must pass with 0 errors
grep -r "claude-haiku-\|claude-sonnet-\|claude-opus-" src/agents/  # must return empty
```

### Agent File → Role Mapping

| Agent File | Role |
|------------|------|
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

---

## 6. Governance

### Adding a New Model

Before deploying a new model to production:
- [ ] Benchmarked on 10+ real tasks
- [ ] Success rate ≥ baseline (or justified exception)
- [ ] Cost-performance analyzed
- [ ] Added to `models.yaml` with all provider mappings
- [ ] OpenTelemetry spans updated (`model_name` attribute)
- [ ] Fallback strategy documented
- [ ] `make verify-models` passes

### Review Cadence

- **Monthly**: Check Model Engineer recommendations, update costs
- **Quarterly**: Evaluate new models from other vendors, benchmark
- **Semi-annually**: Deep cost analysis, potential model swaps
- **Ad-hoc**: When new capabilities needed or vendor changes pricing

---

## See Also

- **`models.yaml`** — Single source of truth for role → model mappings
- **`orchestration/agents/model_resolver.py`** — ModelResolver implementation
- **`docs/SPEC.md`** — Agent specifications table
- **`docs/architecture/`** — Other architecture documents
