#!/usr/bin/env bash
# .githooks/LOCKED_MODELS.sh
#
# GENERATED from config/models.yaml by scripts/models.py sync - do not edit by hand.
# config/models.yaml is the source of truth; regenerate with: make models-sync.
# To change pins, follow the Model Pin Change process in docs/SPEC.md.
#
# Sourcing API (stable): LOCKED_MODELS, AGENT_MODEL_ASSIGNMENTS, is_model_locked,
# get_agent_locked_model, show_locked_models, show_agent_assignments.
#
# Bypass: SKIP_HOOKS=1 (emergency only; document the reason in the commit message)

LOCKED_MODELS=(
    "claude-haiku-4.5"
    "claude-sonnet-4.5"
    "claude-sonnet-4.6"
    "claude-sonnet-5"
    "claude-sonnet-5.5"
    "claude-opus-4.6"
    "claude-opus-4.7"
    "claude-opus-4.8"
    "claude-opus-5"
    "claude-opus-5.5"
    "claude-fable-5"
)

# Fallback behaviour when a pinned model is unavailable is defined per role in
# config/models.yaml (see docs/MODELS.md); it is not decided in this file.

# ─── AGENT-MODEL MAPPING: Which agent uses which model ──────────────────────
# Generated from the roles section of config/models.yaml (role pins).
# Format: agent-name:model-choice (space-separated for portability)
AGENT_MODEL_ASSIGNMENTS=(
    "engineer-agent:claude-haiku-4.5"
    "orchestrator-agent:claude-sonnet-5.5"
    "lead-engineer-agent:claude-sonnet-5.5"
    "quality-engineer-agent:claude-sonnet-5.5"
    "senior-engineer-agent:claude-sonnet-5.5"
    "model-engineer-agent:claude-sonnet-5.5"
    "security-engineer-agent:claude-fable-5"
    "principal-engineer-agent:claude-opus-5.5"
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

# ─── INTERACTIVE / DIAGNOSTIC HELPERS ────────────────────────────────────────
# The three functions below (get_agent_locked_model, show_locked_models,
# show_agent_assignments) have NO caller anywhere in this repo — only
# is_model_locked() above is invoked by a hook (.githooks/pre-commit). They are
# kept, and exported, as the documented sourcing API for interactive use:
#   source .githooks/LOCKED_MODELS.sh && show_agent_assignments
# See LOCKED_MODELS_RATIONALE.md § "Enforcement Mechanism". Do not delete them
# expecting to remove dead code — delete them only alongside that documented API.

# Get the locked model for a specific agent.
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

