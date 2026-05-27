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

# ─── LOCKED MODELS: Canonical list (only these are allowed in agents) ────────
# Format: claude-{variant}-{major}.{minor}
declare -a LOCKED_MODELS=(
    "claude-haiku-4.5"
    "claude-sonnet-4.5"
    "claude-sonnet-4.6"
    "claude-opus-4.7"
)

# ─── AGENT-MODEL MAPPING: Which agent uses which model ──────────────────────
# This is the canonical assignment. Agents MUST use a model from this mapping.
# Format: agent-role → model-choice
declare -A AGENT_MODEL_MAPPING=(
    [engineer-agent]="claude-haiku-4.5"
    [orchestrator-agent]="claude-haiku-4.5"
    [lead-engineer-agent]="claude-sonnet-4.6"
    [quality-engineer-agent]="claude-sonnet-4.6"
    [senior-engineer-agent]="claude-sonnet-4.6"
    [model-engineer-agent]="claude-sonnet-4.5"
    [security-engineer-agent]="claude-opus-4.7"
    [principal-engineer-agent]="claude-opus-4.7"
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
    
    # Check if agent exists in mapping using local variable expansion
    if [[ -n "${AGENT_MODEL_MAPPING[$agent_role]:-}" ]]; then
        echo "${AGENT_MODEL_MAPPING[$agent_role]}"
        return 0
    else
        return 1  # Agent not in mapping
    fi
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
    for agent in "${!AGENT_MODEL_MAPPING[@]}"; do
        echo "  - $agent: ${AGENT_MODEL_MAPPING[$agent]}"
    done | sort
}

# ─── EXPORT for sourcing in other hooks ───────────────────────────────────────
export LOCKED_MODELS
export AGENT_MODEL_MAPPING
export -f is_model_locked
export -f get_agent_locked_model
export -f show_locked_models
export -f show_agent_assignments
