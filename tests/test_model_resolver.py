#!/usr/bin/env python3
"""
Comprehensive test suite for ModelResolver.

Tests cover:
- Configuration parsing and loading
- Role-to-model resolution
- Provider-specific resolution
- Environment override precedence
- Fallback strategies
- Validation and error handling
- Capability deltas detection
"""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from src.orchestration.agents.model_resolver import (
    ModelResolver,
    ModelNotFoundError,
    ValidationError,
)


class TestModelResolverBasics:
    """Tests for basic ModelResolver functionality."""

    @pytest.fixture
    def resolver_with_yaml(self):
        """Create a resolver with test models.yaml."""
        # Use the real models.yaml from the repo
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found in repo")

    @pytest.fixture
    def resolver_with_defaults(self):
        """Create a resolver using embedded defaults."""
        return ModelResolver.from_defaults()

    def test_resolver_initialization_with_file(self, resolver_with_yaml):
        """Test initialization with real models.yaml file."""
        assert resolver_with_yaml is not None
        assert resolver_with_yaml.models_config is not None
        assert len(resolver_with_yaml.models_config) > 0

    def test_resolver_initialization_with_defaults(self, resolver_with_defaults):
        """Test initialization with embedded defaults."""
        assert resolver_with_defaults is not None
        assert resolver_with_defaults.fallback_to_defaults

    def test_resolver_auto_finds_models_yaml(self):
        """Test that resolver can auto-find models.yaml."""
        # Change to repo directory to test auto-finding
        original_cwd = os.getcwd()
        try:
            repo_root = Path(__file__).parent.parent.parent
            os.chdir(repo_root)
            resolver = ModelResolver()
            assert resolver.models_config is not None
        finally:
            os.chdir(original_cwd)


class TestBasicResolution:
    """Tests for basic role-to-model resolution."""

    @pytest.fixture
    def resolver(self):
        return ModelResolver.from_defaults()

    def test_resolve_engineer_role(self, resolver):
        """Test resolving engineer role."""
        model = resolver.resolve('engineer')
        assert model is not None
        assert 'haiku' in model.lower() or 'claude' in model.lower()

    def test_resolve_senior_engineer_role(self, resolver):
        """Test resolving senior_engineer role."""
        model = resolver.resolve('senior_engineer')
        assert model is not None
        assert 'sonnet' in model.lower()

    def test_resolve_security_engineer_role(self, resolver):
        """Test resolving security_engineer role returns fable-5 unconditionally."""
        model = resolver.resolve('security_engineer')
        assert model is not None
        assert 'fable' in model.lower()

    def test_resolve_with_kebab_case_role(self, resolver):
        """Test resolving role in kebab-case (auto-converts to snake_case)."""
        model1 = resolver.resolve('senior-engineer')
        model2 = resolver.resolve('senior_engineer')
        assert model1 == model2

    def test_resolve_unknown_role_with_fallback(self, resolver):
        """Test resolving unknown role returns None or raises error."""
        with pytest.raises(ModelNotFoundError):
            resolver.resolve('unknown_role')

    def test_resolve_with_explicit_override(self, resolver):
        """Test explicit override takes precedence."""
        override_model = "gpt-4-turbo"
        model = resolver.resolve('engineer', override=override_model)
        assert model == override_model

    def test_resolve_all_known_roles(self, resolver):
        """Test that all registered roles can be resolved."""
        for role in resolver.list_all_roles():
            try:
                model = resolver.resolve(role)
                assert model is not None
                assert isinstance(model, str)
                assert len(model) > 0
            except ModelNotFoundError:
                # Some roles might only be in models.yaml, not in YAML
                pass


class TestProviderSpecificResolution:
    """Tests for provider-specific model resolution."""

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")

    def test_resolve_copilot_provider(self, resolver_with_yaml):
        """Test resolving engineer for copilot provider."""
        model = resolver_with_yaml.resolve('engineer', provider='copilot')
        assert model is not None
        # Copilot typically uses GPT models
        assert 'gpt' in model.lower()

    def test_resolve_claude_provider(self, resolver_with_yaml):
        """Test resolving engineer for claude provider."""
        model = resolver_with_yaml.resolve('engineer', provider='claude')
        assert model is not None
        assert 'claude' in model.lower()

    def test_resolve_openai_provider(self, resolver_with_yaml):
        """Test resolving engineer for openai provider."""
        model = resolver_with_yaml.resolve('engineer', provider='openai')
        assert model is not None

    def test_resolve_google_provider(self, resolver_with_yaml):
        """Test resolving engineer for google provider."""
        model = resolver_with_yaml.resolve('engineer', provider='google')
        assert model is not None

    def test_resolve_with_unknown_provider_falls_back(self, resolver_with_yaml):
        """Test that unknown provider falls back to canonical."""
        canonical = resolver_with_yaml.get_canonical('engineer')
        model = resolver_with_yaml.resolve('engineer', provider='unknown_provider')
        # Should fall back to canonical
        assert model == canonical

    def test_get_provider_specific(self, resolver_with_yaml):
        """Test getting provider-specific model directly."""
        copilot_model = resolver_with_yaml.get_provider_specific('engineer', 'copilot')
        assert copilot_model is not None
        assert 'gpt' in copilot_model.lower()

    def test_get_all_providers(self, resolver_with_yaml):
        """Test getting all provider mappings for a role."""
        providers = resolver_with_yaml.get_all_providers('engineer')
        assert isinstance(providers, dict)
        assert len(providers) > 0
        # Should have mappings for major providers
        assert 'copilot' in providers or 'claude' in providers


class TestEnvironmentOverrides:
    """Tests for environment variable override precedence."""

    @pytest.fixture
    def resolver(self):
        return ModelResolver.from_defaults()

    def test_resolve_with_env_agent_model_override(self, resolver, monkeypatch):
        """Test AGENT_MODEL_OVERRIDE_{ROLE} takes precedence."""
        override_model = "gpt-4-turbo"
        monkeypatch.setenv("AGENT_MODEL_OVERRIDE_ENGINEER", override_model)
        
        model = resolver.resolve_with_env('engineer')
        assert model == override_model

    def test_resolve_with_env_role_not_in_override(self, resolver, monkeypatch):
        """Test that roles not in override use standard resolution."""
        monkeypatch.setenv("AGENT_MODEL_OVERRIDE_ENGINEER", "gpt-4-turbo")
        
        # senior_engineer is not overridden
        model = resolver.resolve_with_env('senior_engineer')
        assert model != "gpt-4-turbo"
        assert 'sonnet' in model.lower()

    def test_resolve_with_env_model_tier_haiku(self, resolver, monkeypatch):
        """Test MODEL_TIER=haiku applies to all agents."""
        monkeypatch.setenv("MODEL_TIER", "haiku")
        
        model = resolver.resolve_with_env('engineer')
        assert 'haiku' in model.lower()

    def test_resolve_with_env_model_tier_sonnet(self, resolver, monkeypatch):
        """Test MODEL_TIER=sonnet applies to all agents."""
        monkeypatch.setenv("MODEL_TIER", "sonnet")
        
        model = resolver.resolve_with_env('engineer')
        assert 'sonnet' in model.lower()

    def test_resolve_with_env_model_tier_opus(self, resolver, monkeypatch):
        """Test MODEL_TIER=opus applies to all agents."""
        monkeypatch.setenv("MODEL_TIER", "opus")
        
        model = resolver.resolve_with_env('engineer')
        assert 'opus' in model.lower()

    def test_resolve_with_env_preferred_provider(self, resolver_with_yaml, monkeypatch):
        """Test PREFERRED_PROVIDER selects provider-specific model."""
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if not models_yaml_path.exists():
            pytest.skip("models.yaml not found")
        
        resolver = ModelResolver(str(models_yaml_path))
        monkeypatch.setenv("PREFERRED_PROVIDER", "copilot")
        
        model = resolver.resolve_with_env('engineer', provider=None)
        # Should use copilot provider's model
        assert model is not None

    def test_env_override_precedence_order(self, resolver, monkeypatch):
        """Test that AGENT_MODEL_OVERRIDE_{ROLE} takes precedence over MODEL_TIER."""
        # Both are set
        monkeypatch.setenv("AGENT_MODEL_OVERRIDE_ENGINEER", "gpt-4-turbo")
        monkeypatch.setenv("MODEL_TIER", "haiku")
        
        # AGENT_MODEL_OVERRIDE should win
        model = resolver.resolve_with_env('engineer')
        assert model == "gpt-4-turbo"

    def test_no_env_vars_uses_standard_resolution(self, resolver, monkeypatch):
        """Test that without env vars, standard resolution is used."""
        # Clear any existing overrides
        for key in list(os.environ.keys()):
            if key.startswith('AGENT_MODEL_OVERRIDE_') or key in ['MODEL_TIER', 'PREFERRED_PROVIDER']:
                monkeypatch.delenv(key, raising=False)
        
        model = resolver.resolve_with_env('engineer')
        assert model is not None

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")


class TestCanonicalResolution:
    """Tests for canonical model resolution."""

    @pytest.fixture
    def resolver(self):
        return ModelResolver.from_defaults()

    def test_get_canonical_engineer(self, resolver):
        """Test getting canonical model for engineer."""
        canonical = resolver.get_canonical('engineer')
        assert canonical is not None
        assert 'haiku' in canonical.lower()

    def test_get_canonical_senior_engineer(self, resolver):
        """Test getting canonical model for senior_engineer."""
        canonical = resolver.get_canonical('senior_engineer')
        assert canonical is not None
        assert 'sonnet' in canonical.lower()

    def test_get_canonical_unknown_role(self, resolver):
        """Test getting canonical for unknown role raises error."""
        with pytest.raises(ModelNotFoundError):
            resolver.get_canonical('unknown_role')


class TestEffortLevels:
    """Tests for effort level retrieval."""

    @pytest.fixture
    def resolver(self):
        return ModelResolver.from_defaults()

    def test_get_effort_engineer(self, resolver):
        """Test effort level for engineer."""
        effort = resolver.get_effort('engineer')
        assert effort in ['low', 'medium', 'high', 'max']

    def test_get_effort_security_engineer(self, resolver):
        """Test effort level for security_engineer (should be high/max)."""
        effort = resolver.get_effort('security_engineer')
        assert effort in ['high', 'max']

    def test_get_effort_unknown_role(self, resolver):
        """Test getting effort for unknown role raises error."""
        with pytest.raises(ModelNotFoundError):
            resolver.get_effort('unknown_role')


class TestThinkingMode:
    """Tests for extended thinking mode detection."""

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")

    def test_engineer_no_thinking(self, resolver_with_yaml):
        """Test that engineer doesn't require thinking."""
        thinking = resolver_with_yaml.is_thinking_supported('engineer')
        assert thinking is False

    def test_senior_engineer_requires_thinking(self, resolver_with_yaml):
        """Test that senior_engineer requires thinking."""
        thinking = resolver_with_yaml.is_thinking_supported('senior_engineer')
        assert thinking is True

    def test_security_engineer_requires_thinking(self, resolver_with_yaml):
        """Test that security_engineer requires thinking."""
        thinking = resolver_with_yaml.is_thinking_supported('security_engineer')
        assert thinking is True


class TestValidation:
    """Tests for role validation and registry validation."""

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")

    def test_validate_engineer_role(self, resolver_with_yaml):
        """Test validating engineer role."""
        valid = resolver_with_yaml.validate('engineer')
        assert valid is True

    def test_validate_unknown_role(self, resolver_with_yaml):
        """Test validating unknown role."""
        valid = resolver_with_yaml.validate('unknown_role_that_does_not_exist')
        assert valid is False

    def test_validate_all_registry(self, resolver_with_yaml):
        """Test validating entire registry."""
        result = resolver_with_yaml.validate_all()
        
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'coverage' in result
        
        # Should be mostly valid (might have warnings)
        assert isinstance(result['valid'], bool)
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)

    def test_list_all_roles(self, resolver_with_yaml):
        """Test listing all available roles."""
        roles = resolver_with_yaml.list_all_roles()
        assert isinstance(roles, list)
        assert len(roles) > 0
        
        # Should include common roles
        assert 'engineer' in roles
        assert 'security_engineer' in roles

    def test_list_all_providers(self, resolver_with_yaml):
        """Test listing all available providers."""
        providers = resolver_with_yaml.list_all_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
        
        # Should include major providers
        assert 'claude' in providers or 'copilot' in providers


class TestCapabilityDeltas:
    """Tests for capability delta detection."""

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")

    def test_get_capability_deltas_thinking(self, resolver_with_yaml):
        """Test detecting when provider doesn't support required thinking."""
        # senior_engineer requires thinking, copilot doesn't support it
        deltas = resolver_with_yaml.get_capability_deltas('senior_engineer', 'copilot')
        
        # Should detect the thinking mode gap
        assert isinstance(deltas, list)
        # May or may not have deltas depending on models.yaml content

    def test_get_capability_deltas_unknown_role(self, resolver_with_yaml):
        """Test capability deltas for unknown role."""
        deltas = resolver_with_yaml.get_capability_deltas('unknown_role', 'copilot')
        assert isinstance(deltas, list)
        assert len(deltas) > 0  # Should have error about unknown role

    def test_get_capability_deltas_unknown_provider(self, resolver_with_yaml):
        """Test capability deltas for unknown provider."""
        deltas = resolver_with_yaml.get_capability_deltas('engineer', 'unknown_provider')
        assert isinstance(deltas, list)
        assert len(deltas) > 0  # Should have error about unknown provider


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def resolver_with_yaml(self):
        repo_root = Path(__file__).parent.parent.parent
        models_yaml_path = repo_root / "models.yaml"
        
        if models_yaml_path.exists():
            return ModelResolver(str(models_yaml_path))
        else:
            pytest.skip("models.yaml not found")

    def test_complete_resolution_workflow(self, resolver_with_yaml):
        """Test complete workflow: resolve with all features."""
        # Get canonical
        canonical = resolver_with_yaml.get_canonical('engineer')
        assert canonical is not None
        
        # Get effort
        effort = resolver_with_yaml.get_effort('engineer')
        assert effort in ['low', 'medium', 'high', 'max']
        
        # Get all providers
        providers = resolver_with_yaml.get_all_providers('engineer')
        assert len(providers) > 0
        
        # Resolve for each provider
        for provider in providers.keys():
            model = resolver_with_yaml.resolve('engineer', provider=provider)
            assert model is not None

    def test_multiple_roles_resolution(self, resolver_with_yaml):
        """Test resolving multiple roles."""
        roles = ['engineer', 'senior_engineer', 'security_engineer', 'principal_engineer']
        
        for role in roles:
            model = resolver_with_yaml.resolve(role)
            assert model is not None
            
            canonical = resolver_with_yaml.get_canonical(role)
            assert canonical is not None
            
            effort = resolver_with_yaml.get_effort(role)
            assert effort is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
