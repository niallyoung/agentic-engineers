#!/usr/bin/env python3
"""
tests/test_config_naming_consistency.py — Model-naming consistency guard.

Task: consolidation-p1-config-naming-standardization

Codifies the project's two-layer model-naming convention so future config
edits cannot introduce drift. The convention (see src/config/CONFIG-README.md
and the docstring of ModelResolver) is:

  Layer 1 — CANONICAL (short, version-agnostic):  ``claude-haiku``
      Used ONLY in ``models.yaml`` ``role_models.<role>.canonical``.
      It names a *model family*, not a concrete API model id.

  Layer 2 — RESOLVED (full version):  ``claude-haiku-4.5``
      Used everywhere a concrete model assignment is needed:
        * models.yaml  -> providers.<harness>, cost rates, model_selection
        * model-config.yaml -> agent/task/experiment assignments, cost tiers
        * .githooks/LOCKED_MODELS.sh -> LOCKED_MODELS + AGENT_MODEL_ASSIGNMENTS
        * model_resolver.FALLBACK_DEFAULTS

These two layers are intentional, not a style inconsistency: A/B experiments
and the locked-models enforcement hook distinguish, e.g., ``claude-opus-4.6``
from ``claude-opus-4.8``. Collapsing version-tracking contexts to short names
would destroy information. This test therefore enforces:

  * canonical fields use ONLY short names (no version suffix)
  * every version-tracking context uses ONLY full-version names (with suffix)
  * the same style is applied consistently *within* each context
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "src" / "config"
LOCKED_MODELS_SH = REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh"

# A Claude model token of either layer, e.g. "claude-haiku" or "claude-opus-4.8".
CLAUDE_TOKEN = re.compile(r"claude-(?:haiku|sonnet|opus|fable)[\w.\-]*")

# Full-version names carry a numeric version suffix. Two accepted shapes:
#   claude-<variant>-<major>.<minor>   e.g. claude-haiku-4.5
#   claude-fable-<n>                   e.g. claude-fable-5 (single-part by design)
FULL_VERSION = re.compile(
    r"^claude-(?:haiku|sonnet|opus)-\d+\.\d+$|^claude-fable-\d+$"
)

# Short (canonical) names carry NO version suffix.
SHORT_NAME = re.compile(r"^claude-(?:haiku|sonnet|opus|fable)$")


def _is_full_version(name: str) -> bool:
    return bool(FULL_VERSION.match(name))


def _is_short(name: str) -> bool:
    return bool(SHORT_NAME.match(name))


def _all_claude_tokens(text: str):
    return CLAUDE_TOKEN.findall(text)


# ---------------------------------------------------------------------------
# models.yaml — the only file that legitimately mixes both layers
# ---------------------------------------------------------------------------

def _load_models_yaml() -> dict:
    with open(CONFIG_DIR / "models.yaml") as fh:
        return yaml.safe_load(fh)


def test_models_yaml_canonical_fields_are_short_names():
    """role_models.<role>.canonical must use short (version-agnostic) names."""
    data = _load_models_yaml()
    role_models = data.get("role_models", {})
    assert role_models, "role_models section missing from models.yaml"
    for role, cfg in role_models.items():
        canonical = cfg.get("canonical")
        assert canonical, f"{role}: missing canonical field"
        assert _is_short(canonical), (
            f"{role}.canonical = {canonical!r} is not a short canonical name "
            f"(expected e.g. 'claude-haiku' with no version suffix)"
        )


def test_models_yaml_provider_assignments_are_full_versions():
    """providers.<harness> entries must use full-version model ids."""
    data = _load_models_yaml()
    for role, cfg in data.get("role_models", {}).items():
        for harness in ("copilot", "claude"):
            name = cfg.get("providers", {}).get(harness)
            assert name, f"{role}: missing providers.{harness}"
            assert _is_full_version(name), (
                f"{role}.providers.{harness} = {name!r} must be a full-version "
                f"name (e.g. 'claude-haiku-4.5')"
            )


def test_models_yaml_cost_and_selection_tables_are_full_versions():
    """Cost-rate and model_selection Claude keys must be full-version names."""
    data = _load_models_yaml()
    anthropic_rates = data.get("providers", {}).get("anthropic", {})
    selection = data.get("model_selection", {}).get("models", {})
    for table_name, table in (("providers.anthropic", anthropic_rates),
                              ("model_selection.models", selection)):
        claude_keys = [k for k in table if k.startswith("claude-")]
        assert claude_keys, f"{table_name}: no claude-* keys found"
        for key in claude_keys:
            assert _is_full_version(key), (
                f"{table_name}: key {key!r} must be a full-version name"
            )


# ---------------------------------------------------------------------------
# Version-tracking contexts — must be 100% full-version, no short leakage
# ---------------------------------------------------------------------------

def _assert_text_all_full_versions(text: str, label: str):
    tokens = _all_claude_tokens(text)
    assert tokens, f"{label}: no claude model names found (unexpected)"
    short_leaks = sorted({t for t in tokens if _is_short(t)})
    assert not short_leaks, (
        f"{label}: short canonical name(s) leaked into a version-tracking "
        f"context: {short_leaks}. Use full-version names "
        f"(e.g. 'claude-haiku-4.5') here."
    )
    # Every token must match either full-version or short; since short is
    # disallowed above, surviving tokens must be full-version.
    malformed = sorted({
        t for t in tokens
        if not _is_full_version(t) and not _is_short(t)
    })
    assert not malformed, (
        f"{label}: malformed model name(s) (neither short nor full-version): "
        f"{malformed}"
    )


def test_model_config_yaml_uses_full_versions():
    text = (CONFIG_DIR / "model-config.yaml").read_text()
    _assert_text_all_full_versions(text, "model-config.yaml")


def test_locked_models_sh_uses_full_versions():
    text = LOCKED_MODELS_SH.read_text()
    _assert_text_all_full_versions(text, "LOCKED_MODELS.sh")


def test_resolver_fallback_defaults_use_full_versions():
    """ModelResolver derives FALLBACK_DEFAULTS from models.yaml's claude
    provider mapping; every derived value must be a full-version name so it
    matches what resolve() returns when the registry is present."""
    from src.orchestration.agents.model_resolver import ModelResolver

    resolver = ModelResolver()  # derives FALLBACK_DEFAULTS from models.yaml
    defaults = resolver.FALLBACK_DEFAULTS
    assert defaults, "FALLBACK_DEFAULTS derived empty"
    for role, model in defaults.items():
        assert _is_full_version(model), (
            f"FALLBACK_DEFAULTS[{role!r}] = {model!r} must be a full-version "
            f"name to match what resolve() returns from models.yaml"
        )


# ---------------------------------------------------------------------------
# Cross-file agreement — the locked hook, config, and resolver must agree
# ---------------------------------------------------------------------------

def _parse_locked_assignments() -> dict:
    """Parse AGENT_MODEL_ASSIGNMENTS array from LOCKED_MODELS.sh."""
    text = LOCKED_MODELS_SH.read_text()
    block = re.search(
        r"AGENT_MODEL_ASSIGNMENTS=\((.*?)\)", text, re.DOTALL
    )
    assert block, "AGENT_MODEL_ASSIGNMENTS array not found"
    out = {}
    for m in re.finditer(r'"([\w-]+):(claude-[\w.\-]+)"', block.group(1)):
        out[m.group(1)] = m.group(2)
    assert out, "no agent assignments parsed from LOCKED_MODELS.sh"
    return out


def test_locked_assignments_reference_locked_models():
    """Every model assigned to an agent must appear in the LOCKED_MODELS set."""
    text = LOCKED_MODELS_SH.read_text()
    locked_block = re.search(r"LOCKED_MODELS=\((.*?)\)", text, re.DOTALL)
    assert locked_block, "LOCKED_MODELS array not found"
    locked = set(re.findall(r'"(claude-[\w.\-]+)"', locked_block.group(1)))
    assignments = _parse_locked_assignments()
    for agent, model in assignments.items():
        assert model in locked, (
            f"{agent} assigned {model!r} which is not in LOCKED_MODELS {locked}"
        )


def test_model_config_global_default_is_locked():
    """model-config.yaml global default must be an approved (locked) model."""
    with open(CONFIG_DIR / "model-config.yaml") as fh:
        cfg = yaml.safe_load(fh)
    default = cfg["global"]["default_model"]
    assert _is_full_version(default), default
    text = LOCKED_MODELS_SH.read_text()
    locked_block = re.search(r"LOCKED_MODELS=\((.*?)\)", text, re.DOTALL)
    locked = set(re.findall(r'"(claude-[\w.\-]+)"', locked_block.group(1)))
    assert default in locked, (
        f"global.default_model {default!r} not in LOCKED_MODELS {locked}"
    )
