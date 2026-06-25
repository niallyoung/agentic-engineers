#!/usr/bin/env python3
"""
Tests for the canonical ModelResolver (single source of truth).

Covers:
- FALLBACK_DEFAULTS is derived from models.yaml (drift prevention via asserting test)
- fable-5 defensive-only routing for security_engineer
- backwards-compatible wrapper import path
- agent→model assignments unchanged vs canonical config
"""

from pathlib import Path

import yaml
import pytest

from src.orchestration.models.canonical_resolver import (
    ModelResolver,
    ModelNotFoundError,
    FABLE_5_MODEL,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_YAML = REPO_ROOT / "src" / "config" / "models.yaml"


@pytest.fixture
def resolver():
    return ModelResolver(str(CANONICAL_YAML), fallback_to_defaults=True)


@pytest.fixture
def canonical_config():
    with open(CANONICAL_YAML) as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# AC2: FALLBACK_DEFAULTS derived from models.yaml with asserting test
# ---------------------------------------------------------------------------

class TestFallbackDefaultsDerivedFromYaml:
    def test_fallback_defaults_match_canonical_claude_models(self, resolver, canonical_config):
        """Every role's fallback default must equal its claude-provider model
        from models.yaml. This asserting test prevents future drift."""
        role_models = canonical_config["role_models"]
        for role, cfg in role_models.items():
            expected = cfg["providers"]["claude"]
            assert resolver.FALLBACK_DEFAULTS[role] == expected, (
                f"FALLBACK_DEFAULTS[{role}]={resolver.FALLBACK_DEFAULTS[role]!r} "
                f"drifted from canonical claude model {expected!r}"
            )

    def test_senior_engineer_default_is_canonical_not_drifted(self, resolver):
        """Regression: the old hardcoded default was claude-sonnet-4.6, which
        disagreed with the canonical policy (claude-sonnet-4.5)."""
        assert resolver.FALLBACK_DEFAULTS["senior_engineer"] == "claude-sonnet-4.5"

    def test_from_defaults_derives_same_values(self, canonical_config):
        """from_defaults() (no explicit path) must derive identical values."""
        derived = ModelResolver.from_defaults()
        role_models = canonical_config["role_models"]
        for role, cfg in role_models.items():
            assert derived.FALLBACK_DEFAULTS[role] == cfg["providers"]["claude"]

    def test_no_hardcoded_drift_for_all_eight_agents(self, resolver, canonical_config):
        """All 8 canonical agents resolve to their canonical claude model."""
        for role in canonical_config["role_models"]:
            assert resolver.resolve(role, provider="claude") == \
                canonical_config["role_models"][role]["providers"]["claude"]


# ---------------------------------------------------------------------------
# AC4: fable-5 supported for security_engineer (defensive-only)
# ---------------------------------------------------------------------------

class TestFable5Routing:
    def test_security_engineer_default_is_opus(self, resolver):
        """Default (non-defensive) security_engineer assignment unchanged."""
        assert resolver.resolve("security_engineer", provider="claude") == "claude-opus-4.8"

    def test_security_engineer_defensive_routes_to_fable5(self, resolver):
        assert resolver.resolve("security_engineer", defensive=True) == FABLE_5_MODEL
        assert FABLE_5_MODEL == "claude-fable-5"

    def test_defensive_flag_ignored_for_non_security_roles(self, resolver):
        """defensive=True must not affect any other role."""
        assert resolver.resolve("engineer", defensive=True) != FABLE_5_MODEL

    def test_fable5_in_locked_models(self):
        """LOCKED_MODELS.sh must contain the fable-5 entry."""
        locked = (REPO_ROOT / ".githooks" / "LOCKED_MODELS.sh").read_text()
        assert "claude-fable-5" in locked

    def test_fable5_in_canonical_model_selection(self, canonical_config):
        assert "claude-fable-5" in canonical_config["model_selection"]["models"]


# ---------------------------------------------------------------------------
# AC3: backwards-compatible wrapper import path
# ---------------------------------------------------------------------------

class TestWrapperCompatibility:
    def test_old_agents_path_reexports_canonical(self):
        from src.orchestration.agents.model_resolver import ModelResolver as WrappedResolver
        assert WrappedResolver is ModelResolver

    def test_models_package_exports_resolver(self):
        from src.orchestration.models import ModelResolver as PkgResolver
        assert PkgResolver is ModelResolver


# ---------------------------------------------------------------------------
# AC6: assignments unchanged (logic migration only)
# ---------------------------------------------------------------------------

class TestAssignmentsUnchanged:
    EXPECTED_CLAUDE_ASSIGNMENTS = {
        "engineer": "claude-haiku-4.5",
        "senior_engineer": "claude-sonnet-4.5",
        "quality_engineer": "claude-sonnet-4.6",
        "lead_engineer": "claude-sonnet-4.6",
        "security_engineer": "claude-opus-4.8",
        "principal_engineer": "claude-opus-4.6",
        "model_engineer": "claude-sonnet-4.5",
        "general_orchestrator": "claude-haiku-4.5",
    }

    def test_all_claude_assignments(self, resolver):
        for role, model in self.EXPECTED_CLAUDE_ASSIGNMENTS.items():
            assert resolver.resolve(role, provider="claude") == model

    def test_unknown_role_raises(self, resolver):
        with pytest.raises(ModelNotFoundError):
            resolver.resolve("does_not_exist")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
