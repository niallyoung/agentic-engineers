"""
Test: Model Resolver FALLBACK_DEFAULTS Consistency

Asserts that ModelResolver.FALLBACK_DEFAULTS derived values match the
canonical assignments in models.yaml, ensuring they can never drift.

This is part of Phase 3.1 (security infrastructure consolidation):
ensuring that FALLBACK_DEFAULTS are synchronized with the canonical registry.
"""

import pytest
from pathlib import Path
import yaml

from src.orchestration.models.canonical_resolver import ModelResolver


class TestModelResolverFallbackDefaults:
    """Test FALLBACK_DEFAULTS consistency with models.yaml."""

    def test_fallback_defaults_match_canonical_registry(self):
        """
        Assert that FALLBACK_DEFAULTS are derived from models.yaml and match
        the canonical provider-specific assignments.

        Ensures the values can never drift from the canonical config.
        """
        resolver = ModelResolver()

        # Load the canonical models.yaml to verify against
        canonical_path = resolver._find_models_yaml()
        assert canonical_path is not None, "models.yaml not found"
        assert canonical_path.exists(), f"models.yaml not found at {canonical_path}"

        with open(canonical_path, 'r') as f:
            canonical_config = yaml.safe_load(f)

        role_models = canonical_config.get('role_models', {})
        assert len(role_models) > 0, "models.yaml has no role_models section"

        # For each role in the canonical registry, verify that FALLBACK_DEFAULTS
        # contains the expected value from the 'claude' provider
        for role, role_config in role_models.items():
            assert role in resolver.FALLBACK_DEFAULTS, \
                f"Role '{role}' not in FALLBACK_DEFAULTS"

            # Expected value is the 'claude' provider model
            expected_model = (
                role_config.get('providers', {}).get('claude')
                or role_config.get('canonical')
            )
            assert expected_model is not None, \
                f"Role '{role}' has no 'claude' provider or canonical model"

            actual_model = resolver.FALLBACK_DEFAULTS[role]
            assert actual_model == expected_model, \
                f"Role '{role}': FALLBACK_DEFAULTS['{role}'] = '{actual_model}' " \
                f"but expected '{expected_model}' from models.yaml"

    def test_fallback_defaults_resolve_correctly(self):
        """
        Assert that resolve() without arguments returns FALLBACK_DEFAULTS
        for all roles, demonstrating they are the canonical fallback.
        """
        resolver = ModelResolver()

        for role in resolver.list_all_roles():
            expected = resolver.FALLBACK_DEFAULTS.get(role)
            assert expected is not None, \
                f"Role '{role}' missing from FALLBACK_DEFAULTS"

            # resolve() with no provider argument should return FALLBACK_DEFAULTS
            resolved = resolver.resolve(role)
            assert resolved == expected, \
                f"Role '{role}': resolve() returned '{resolved}' " \
                f"but FALLBACK_DEFAULTS['{role}'] = '{expected}'"

    def test_fallback_defaults_never_empty(self):
        """Assert that FALLBACK_DEFAULTS is always populated (not empty)."""
        resolver = ModelResolver()
        assert len(resolver.FALLBACK_DEFAULTS) > 0, \
            "FALLBACK_DEFAULTS should never be empty"

    def test_all_fallback_defaults_resolve_successfully(self):
        """Assert that all FALLBACK_DEFAULTS values are valid models."""
        resolver = ModelResolver()

        for role, model in resolver.FALLBACK_DEFAULTS.items():
            # Should be a non-empty string
            assert isinstance(model, str), \
                f"FALLBACK_DEFAULTS['{role}'] is not a string: {model}"
            assert len(model) > 0, \
                f"FALLBACK_DEFAULTS['{role}'] is empty"

            # Model should follow canonical naming pattern (e.g., claude-*, gpt-*)
            # or be an alias reference
            assert any(
                model.startswith(prefix)
                for prefix in ['claude-', 'gpt-', 'gemini-', 'llama-']
            ), f"FALLBACK_DEFAULTS['{role}'] = '{model}' doesn't match known model pattern"

    def test_provider_specific_models_available(self):
        """Assert that provider-specific model mappings are available."""
        resolver = ModelResolver()

        # For each role, verify that 'claude' provider is available
        # (since claude is the canonical fallback provider)
        canonical_path = resolver._find_models_yaml()
        if canonical_path and canonical_path.exists():
            with open(canonical_path, 'r') as f:
                canonical_config = yaml.safe_load(f)

            role_models = canonical_config.get('role_models', {})
            for role in role_models.keys():
                providers = resolver.get_all_providers(role)
                assert 'claude' in providers, \
                    f"Role '{role}' missing 'claude' provider in models.yaml"

    def test_fable5_is_unconditional_security_engineer_default(self):
        """security_engineer resolves to fable-5 regardless of the deprecated flag.

        The defensive-only gate was removed; fable-5 is now the unconditional
        default. The `defensive` kwarg is retained for backwards compatibility
        and must be a no-op for every role. Offensive-scope work is rejected by
        the DelegateValidator C5 gate, not by model routing.
        """
        resolver = ModelResolver()

        assert resolver.resolve('security_engineer') == 'claude-fable-5', \
            "security_engineer should default to claude-fable-5"

        # The deprecated flag must not change routing in either direction.
        assert resolver.resolve('security_engineer', defensive=False) == 'claude-fable-5', \
            "defensive=False must not downgrade security_engineer off fable-5"
        assert resolver.resolve('security_engineer', defensive=True) == 'claude-fable-5', \
            "defensive=True must still resolve to claude-fable-5"

        # Other roles are unaffected by the flag and never routed to fable-5.
        engineer_normal = resolver.resolve('engineer', defensive=False)
        engineer_defensive = resolver.resolve('engineer', defensive=True)
        assert engineer_normal == engineer_defensive, \
            "Non-security roles should ignore defensive flag"
        assert engineer_normal != 'claude-fable-5', \
            "fable-5 must never be the default for non-security roles"
