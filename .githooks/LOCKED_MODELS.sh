#!/usr/bin/env bash
# .githooks/LOCKED_MODELS.sh
#
# Single source of truth for model locks (approved model choices).
# These models are LOCKED by choice and cannot be changed without explicit Orchestrator approval.
#
# Philosophy: POSITIVE ENFORCEMENT
# - "We chose these Claude models" (not "GPT is forbidden")
# - Users CAN request model changes by contacting Orchestrator
# - Changes are auditable and explicit
#
# Update this only when Orchestrator explicitly approves a model switch for a named agent.
# Create a PR with:
#   - Commit message: "Approved model switch for {agent} because {reason}"
#   - Rationale in PR description (cost delta, capability improvement, etc)
#
# Bypass: SKIP_HOOKS=1 (for emergency situations only; document reason in commit msg)

# ─── LOCKED MODELS: Canonical list (only these are allowed in agents) ────────
# Format: claude-{variant}-{major}.{minor}
#
# Note: Principal Engineer and Security Engineer support multi-model selection
# within the opus family. The Orchestrator selects the appropriate opus variant
# at DELEGATE-creation time based on task complexity and risk profile.
# See docs/SPEC.md > Model Selection Architecture for the full decision tree.
LOCKED_MODELS=(
    "claude-haiku-4.5"
    "claude-sonnet-4.5"
    "claude-sonnet-4.6"
    "claude-sonnet-5"
    "claude-opus-4.6"
    "claude-opus-4.7"
    "claude-opus-4.8"
    "claude-opus-5"
    "claude-fable-5"
)

# Note: If a locked model becomes unavailable, the harness will auto-select:
# 1. Exact version (preferred)
# 2. Adjacent version in same family (fallback)
# 3. Any version in same family (fallback)
# 4. Any Claude model (fallback)
#
# Examples:
# - prefer claude-sonnet-4.6 → fallback to claude-sonnet-4.5 or claude-sonnet-5.0
# - prefer claude-opus-4.6 → fallback to claude-opus-4.7
# - prefer claude-haiku-4.5 → fallback to claude-haiku-4.6 if it exists

# ─── AGENT-MODEL MAPPING: Which agent uses which model ──────────────────────
# This is the canonical assignment. Agents MUST use a model from this mapping.
# Format: agent-name:model-choice (space-separated for portability)
AGENT_MODEL_ASSIGNMENTS=(
    "engineer-agent:claude-haiku-4.5"
    "orchestrator-agent:claude-sonnet-5"
    "lead-engineer-agent:claude-sonnet-5"
    "quality-engineer-agent:claude-sonnet-5"
    "senior-engineer-agent:claude-sonnet-5"
    "model-engineer-agent:claude-sonnet-5"
    "security-engineer-agent:claude-fable-5"
    "principal-engineer-agent:claude-opus-5"
)

# ─── VALIDATION HELPER: Check if model is in locked set ──────────────────────
is_model_locked() {
    local model="$1"
    
    for locked_model in "${LOCKED_MODELS[@]}"; do
        if [[ "$model" == "$locked_model" ]]; then
            return 0  # Model is locked (approved)
        fi
    done
    
    return 1  # Model is NOT locked (not approved)
}

# ─── VALIDATION HELPER: Get locked models for a specific agent ───────────────
get_agent_locked_model() {
    local agent_role="$1"
    
    # Search for agent in assignments (format: "agent-name:model")
    for assignment in "${AGENT_MODEL_ASSIGNMENTS[@]}"; do
        local agent="${assignment%%:*}"
        local model="${assignment##*:}"
        if [[ "$agent" == "$agent_role" ]]; then
            echo "$model"
            return 0
        fi
    done
    
    return 1  # Agent not found
}

# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────

# Show all locked models (for error messages)
show_locked_models() {
    echo "Locked models (approved choices):"
    for model in "${LOCKED_MODELS[@]}"; do
        echo "  - $model"
    done
}

# Show agent-model assignments (for documentation)
show_agent_assignments() {
    echo "Agent model assignments:"
    for assignment in "${AGENT_MODEL_ASSIGNMENTS[@]}"; do
        local agent="${assignment%%:*}"
        local model="${assignment##*:}"
        echo "  - $agent: $model"
    done | sort
}

# ─── EXPORT for sourcing in other hooks ───────────────────────────────────────
export LOCKED_MODELS
export AGENT_MODEL_ASSIGNMENTS
export -f is_model_locked
export -f get_agent_locked_model
export -f show_locked_models
export -f show_agent_assignments

