# Model Lock Rationale

## Philosophy: Positive Enforcement

We use **positive enforcement** (locked choices) instead of **negative enforcement** (forbidden patterns).

### Why?

**Positive ("We chose these models"):**
- ✅ Clear intent: "These are our approved models"
- ✅ User choice preserved: Model CAN be changed by contacting Orchestrator
- ✅ Auditable: When changes happen, they're explicit decisions with rationale
- ✅ Simpler code: One list of approved models, not multiple rejection patterns

**Negative ("GPT is forbidden"):**
- ❌ Defensive posture: Sounds like we're preventing user choice
- ❌ Hard to maintain: Must update rejection patterns every time a new model appears
- ❌ Less clear intent: "Forbidden" implies restriction, not strategic choice

## Locked Models Today

| Model | Agents | Rationale | Cost/Token |
|-------|--------|-----------|-----------|
| **claude-haiku-4.5** | engineer, orchestrator | Fast, cost-effective for standard tasks | $0.035 |
| **claude-sonnet-4.5** | model-engineer | Analysis tasks, cost-quality balance | $0.06 |
| **claude-sonnet-4.6** | lead, quality, senior | Complex tasks, higher quality | $0.065 |
| **claude-opus-4.7** | security, principal | High-stakes, cross-service decisions | $0.15 |

## Model Switch Process

Models are locked by **explicit choice**, not by chance or restriction. To change:

### 1. Request Phase
Contact Orchestrator with:
- **Agent name** (e.g., `engineer-agent`)
- **Requested model** (e.g., `claude-sonnet-4.5`)
- **Reason** (e.g., "Current model too slow for code review tasks")
- **Expected impact** (e.g., "Cost +$0.02/task, quality +15%")

### 2. Evaluation Phase
Orchestrator evaluates:
- Cost delta (is budget available?)
- Capability improvement (does the task profile justify the switch?)
- Conflict with other agents (does this create inconsistency?)
- Timeline (when does the change take effect?)

### 3. Decision
One of:
- ✅ **Approved**: Proceed to implementation
- ⏸️ **Deferred**: Consider later (e.g., next budget cycle)
- ❌ **Denied**: Explain why (e.g., budget constraint, capability not needed)

### 4. Implementation (if approved)
1. Update `.githooks/LOCKED_MODELS.sh`:
   - Add new model to `LOCKED_MODELS` array (if not already present)
   - Update `AGENT_MODEL_MAPPING` for the agent
2. Create PR with:
   - Commit message: `"Approved model switch for {agent}: {reason}"`
   - PR description: Full rationale, cost impact, expected outcome
3. Merge triggers pre-commit hook validation
4. New lock is enforced from that commit forward

## Examples

### ✅ Approved: "Switch engineer-agent to sonnet for higher quality"

```bash
# Scenario: Engineer agent is struggling with code review quality
# Request: Switch from haiku-4.5 to sonnet-4.5
# Cost impact: +$0.025/task × 50 tasks/day = +$1.25/day budget
# Timeline: Immediate

# Decision: APPROVED (budget available, quality improvement justified)

# Implementation:
# 1. Edit .githooks/LOCKED_MODELS.sh
#    AGENT_MODEL_MAPPING[engineer-agent]="claude-sonnet-4.5"
# 2. Create PR with commit message:
#    "Approved model switch for engineer-agent to sonnet-4.5 (code review quality)"
# 3. Merge, hook validates, new lock takes effect
```

### ⏸️ Deferred: "Consider GPT-4 for principal engineer"

```bash
# Scenario: Principal engineer wants access to GPT-4
# Request: Add gpt-4 to locked models
# Cost impact: Different billing provider, contract negotiation needed
# Timeline: 2-3 months

# Decision: DEFERRED
# Reason: "GPT-4 not in current approved provider contract.
#         Revisit when Anthropic Opus reaches feature parity with GPT-4."
# Action: Document in TODO.md for budget cycle review
```

### ❌ Denied: "Switch all agents to opus for maximum quality"

```bash
# Scenario: User wants all agents to run on Opus
# Request: Change all LOCKED_MODELS to claude-opus-4.7
# Cost impact: ~5x budget increase
# Timeline: Immediate

# Decision: DENIED
# Reason: "Budget constraint. Total monthly cost would increase from $2K to $10K.
#         Revisit if we identify tasks that specifically need Opus.
#         Orchestrator can still delegate high-stakes work to principal-engineer (opus)."
```

## Single Source of Truth

The `.githooks/LOCKED_MODELS.sh` file is the **canonical source** for:
- `LOCKED_MODELS` — all approved models (only these pass pre-commit)
- `AGENT_MODEL_MAPPING` — which agent uses which model (for documentation)

### Importing in Other Scripts

Any hook or script that needs to validate models should source this file:

```bash
#!/usr/bin/env bash
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOKS_DIR/LOCKED_MODELS.sh"

# Now available:
# - LOCKED_MODELS array
# - AGENT_MODEL_MAPPING associative array
# - is_model_locked "$model" function
# - get_agent_locked_model "$agent" function
# - show_locked_models function
# - show_agent_assignments function
```

## Maintaining Locks

### When to Update

- ✅ Orchestrator approves a model switch → update LOCKED_MODELS.sh
- ✅ New model version released → discuss in team, decide collectively
- ❌ Don't update just because a new model is available
- ❌ Don't remove old models arbitrarily (existing agents may still use them)

### When to Add a New Model

1. Wait for Orchestrator approval
2. Add to `LOCKED_MODELS` array (alphabetically)
3. Add to `AGENT_MODEL_MAPPING` for the affected agent(s)
4. Update this documentation
5. Commit with message explaining the change

### When to Deprecate

If an old model is no longer used:
1. Verify NO agents use it (grep all agent files)
2. Document in commit message
3. Remove from LOCKED_MODELS (keep in commit history for audit trail)

## Rationale Comments

Every model lock decision should have context. Examples in commit messages:

```
Approved model switch for security-engineer: claude-opus-4.7

Reason: Security analysis requires high reasoning capability
  - Previous model (sonnet) missed subtle vulnerabilities in 3% of audits
  - Opus adds +$0.08/task cost (~$2/day)
  - Approved by Security Lead and Orchestrator
  
Cost approved for Q2 2025 security initiative.
Revisit in Q3 if vulnerability detection improves in Sonnet.
```

## Governance

- **Approval authority**: Orchestrator (with input from role leads)
- **Appeal**: If denied, request review in next budget cycle
- **Transparency**: All model decisions documented in commit messages
- **Audit trail**: Git history shows who, what, when, why
- **Enforcement**: Pre-commit hook validates compliance

## See Also

- [.githooks/LOCKED_MODELS.sh](./.githooks/LOCKED_MODELS.sh) — Canonical model list
- [SPEC.md](../SPEC.md#approved-claude-models) — Architectural documentation
- [CONTRIBUTING.md](../CONTRIBUTING.md#model-selection) — Contributor guide
