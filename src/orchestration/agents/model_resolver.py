#!/usr/bin/env python3
"""
ModelResolver: Centralized model name resolution for agent-to-model mapping.

This module provides a single source of truth for mapping agent roles to model names
across providers, with support for environment-specific overrides and fallback strategies.

Design: docs/architecture-model-centralization.md
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

logger = logging.getLogger(__name__)

# Enable debug logging with MODEL_RESOLVER_DEBUG=1
if os.getenv("MODEL_RESOLVER_DEBUG"):
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.addHandler(formatter)


class ValidationError(Exception):
    """Raised when model resolution validation fails."""
    pass


class ModelNotFoundError(Exception):
    """Raised when a role is not found in the registry."""
    pass


class ModelResolver:
    """
    Centralizes resolution of role names to model names.
    
    Supports:
    - Parsing models.yaml configuration
    - Converting between canonical and provider-specific formats
    - Environment-specific overrides (CLI > env vars > YAML > defaults)
    - Fallback strategies for missing providers or roles
    - Capability delta detection (thinking mode, structured output, etc.)
    """

    # Fallback defaults when models.yaml is unavailable
    FALLBACK_DEFAULTS = {
        'engineer': 'claude-haiku-4.5',
        'senior_engineer': 'claude-sonnet-4.6',
        'quality_engineer': 'claude-sonnet-4.6',
        'lead_engineer': 'claude-sonnet-4.6',
        'security_engineer': 'claude-opus-4.7',
        'principal_engineer': 'claude-opus-4.7',
        'model_engineer': 'claude-haiku-4.5',
        'general_orchestrator': 'claude-haiku-4.5',
        'orchestrator': 'claude-haiku-4.5',
        'metrics': 'claude-haiku-4.5',
        'testing': 'claude-haiku-4.5',
        'spec_engineer': 'claude-sonnet-4.6',
        'healing_engineer': 'claude-sonnet-4.6',
        'spec_engineer_orchestrator': 'claude-sonnet-4.6',
    }

    def __init__(self, models_yaml_path: Optional[str] = None, fallback_to_defaults: bool = True):
        """
        Initialize resolver from models.yaml file.

        Args:
            models_yaml_path: Path to models.yaml file. If None, auto-detects common locations.
            fallback_to_defaults: If True, use embedded defaults if file not found and requested.

        Raises:
            FileNotFoundError: If models_yaml_path is specified but doesn't exist and
                              fallback_to_defaults is False.
        """
        self.fallback_to_defaults = fallback_to_defaults
        self.models_config: Dict[str, Any] = {}
        self.providers_config: Dict[str, Any] = {}
        self.models_yaml_path: Optional[Path] = None

        # Try to find and load models.yaml
        if models_yaml_path:
            path = Path(models_yaml_path)
        else:
            # Auto-detect common locations
            path = self._find_models_yaml()

        if path and path.exists():
            try:
                self._load_yaml(path)
                self.models_yaml_path = path
                logger.debug(f"Loaded models.yaml from {path}")
            except Exception as e:
                logger.warning(f"Failed to load models.yaml from {path}: {e}")
                if not fallback_to_defaults:
                    raise
        else:
            if models_yaml_path and not fallback_to_defaults:
                raise FileNotFoundError(f"models.yaml not found at {models_yaml_path}")
            logger.warning("models.yaml not found, using embedded defaults")

    @staticmethod
    def _find_models_yaml() -> Optional[Path]:
        """Auto-detect models.yaml in common locations."""
        candidates = [
            # New location: src/config/models.yaml
            Path(__file__).parent.parent.parent / "config" / "models.yaml",
            # Old location: root models.yaml (for backwards compatibility)
            Path("models.yaml"),
            Path(__file__).parent.parent.parent / "models.yaml",
            # Home directory paths
            Path.home() / "git" / "agentic-engineers" / "models.yaml",
            Path.home() / "git" / "agentic-engineers" / "src" / "config" / "models.yaml",
            Path("/home/user/agentic-engineers/models.yaml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _load_yaml(self, path: Path) -> None:
        """Load and parse models.yaml file."""
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise ValueError(f"models.yaml is empty: {path}")
        
        self.models_config = config.get('role_models', {})
        self.providers_config = config.get('provider_features', {})
        
        if not self.models_config:
            raise ValueError("models.yaml missing 'role_models' section")

    def resolve(
        self,
        role: str,
        provider: Optional[str] = None,
        override: Optional[str] = None
    ) -> str:
        """
        Resolve a role name to a model name.

        Args:
            role: Role name (e.g., 'engineer', 'senior_engineer')
            provider: Provider context (e.g., 'copilot', 'claude', 'openai')
            override: Explicit override model name (highest precedence)

        Returns:
            Model name (e.g., 'claude-haiku-4.5' or provider-specific equivalent)

        Raises:
            ModelNotFoundError: If role not found and not in fallback defaults
            ValueError: If override is invalid
        """
        logger.debug(f"resolve(role={role}, provider={provider}, override={override})")

        # Highest precedence: explicit override
        if override:
            logger.debug(f"Using explicit override: {override}")
            return override

        # Normalize role name (kebab-case to snake_case)
        normalized_role = role.replace('-', '_')
        logger.debug(f"Normalized role: {normalized_role}")

        # Get role config
        role_config = self.models_config.get(normalized_role)
        if not role_config and normalized_role in self.FALLBACK_DEFAULTS:
            logger.debug(f"Using fallback default for {normalized_role}")
            return self.FALLBACK_DEFAULTS[normalized_role]
        
        if not role_config:
            if self.fallback_to_defaults and normalized_role in self.FALLBACK_DEFAULTS:
                return self.FALLBACK_DEFAULTS[normalized_role]
            raise ModelNotFoundError(
                f"Role '{role}' not found in models.yaml and not in fallback defaults"
            )

        # Provider-specific resolution
        if provider:
            providers = role_config.get('providers', {})
            if provider in providers:
                model = providers[provider]
                logger.debug(f"Resolved {normalized_role} to {model} for provider {provider}")
                return model
            else:
                logger.debug(f"Provider {provider} not in models.yaml, falling back to canonical")

        # Fall back to canonical model
        canonical = role_config.get('canonical')
        if canonical:
            # Convert canonical to full version (e.g., claude-haiku -> claude-haiku-4.5)
            # For now, assume canonical can be used as-is; version resolution happens elsewhere
            logger.debug(f"Resolved {normalized_role} to canonical: {canonical}")
            return canonical
        
        raise ValueError(f"Role {role} has no canonical model defined")

    def resolve_with_env(self, role: str, provider: Optional[str] = None) -> str:
        """
        Resolve with environment variable precedence.

        Precedence order:
        1. AGENT_MODEL_OVERRIDE_{ROLE} (e.g., AGENT_MODEL_OVERRIDE_ENGINEER)
        2. MODEL_TIER (haiku/sonnet/opus - applies to all agents)
        3. PREFERRED_PROVIDER (uses provider-specific model)
        4. models.yaml provider mapping
        5. models.yaml canonical

        Args:
            role: Role name
            provider: Provider context (optional)

        Returns:
            Resolved model name
        """
        normalized_role = role.replace('-', '_').upper()
        logger.debug(f"resolve_with_env(role={role}, provider={provider})")

        # Check for role-specific override
        override_key = f"AGENT_MODEL_OVERRIDE_{normalized_role}"
        if override_key in os.environ:
            override = os.environ[override_key]
            logger.debug(f"Found {override_key}={override}")
            return override

        # Check for tier override (applies to all)
        tier = os.getenv("MODEL_TIER")
        if tier:
            logger.debug(f"MODEL_TIER={tier}")
            # Map tier to appropriate model for this role
            model = self._resolve_tier_for_role(role, tier)
            if model:
                return model

        # Check for preferred provider
        preferred_provider = os.getenv("PREFERRED_PROVIDER")
        if preferred_provider:
            logger.debug(f"PREFERRED_PROVIDER={preferred_provider}")
            provider = preferred_provider

        # Standard resolution with provider
        return self.resolve(role, provider=provider)

    def _resolve_tier_for_role(self, role: str, tier: str) -> Optional[str]:
        """
        Resolve a role to a model in the specified tier.
        
        Args:
            role: Role name
            tier: Model tier (haiku, sonnet, opus)

        Returns:
            Model name or None if tier is invalid
        """
        tier = tier.lower()
        
        # Map tier to canonical model family
        tier_to_canonical = {
            'haiku': 'claude-haiku',
            'sonnet': 'claude-sonnet',
            'opus': 'claude-opus',
        }
        
        if tier not in tier_to_canonical:
            logger.warning(f"Unknown MODEL_TIER: {tier}")
            return None
        
        canonical = tier_to_canonical[tier]
        logger.debug(f"Tier {tier} maps to canonical {canonical}")
        
        # Find a model that uses this canonical in the registry
        # For now, just return the canonical; caller will convert to full version
        return canonical

    def get_canonical(self, role: str) -> str:
        """
        Get the canonical (provider-independent) model for a role.

        Args:
            role: Role name

        Returns:
            Canonical model name (e.g., 'claude-haiku', 'claude-sonnet')

        Raises:
            ModelNotFoundError: If role not found
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        
        canonical = role_config.get('canonical')
        if not canonical:
            raise ValueError(f"Role {role} has no canonical model defined")
        
        return canonical

    def get_effort(self, role: str) -> str:
        """
        Get the effort level for a role (used for cost tracking).

        Args:
            role: Role name

        Returns:
            Effort level: 'low', 'medium', 'high', or 'max'

        Raises:
            ModelNotFoundError: If role not found
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        
        effort = role_config.get('effort', 'medium')
        return effort

    def is_thinking_supported(self, role: str) -> bool:
        """
        Check if a role requires extended thinking mode.

        Args:
            role: Role name

        Returns:
            True if role requires thinking mode, False otherwise
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        
        if not role_config:
            return False
        
        return role_config.get('thinking', False)

    def get_provider_specific(self, role: str, provider: str) -> Optional[str]:
        """
        Get provider-specific model name for a role.

        Args:
            role: Role name
            provider: Provider name

        Returns:
            Provider-specific model name, or None if not available

        Raises:
            ModelNotFoundError: If role not found
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        
        providers = role_config.get('providers', {})
        return providers.get(provider)

    def get_all_providers(self, role: str) -> Dict[str, str]:
        """
        Get all provider-specific models for a role.

        Args:
            role: Role name

        Returns:
            Dictionary mapping provider names to model names

        Raises:
            ModelNotFoundError: If role not found
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        
        return role_config.get('providers', {})

    def validate(self, role: str) -> bool:
        """
        Check if a role exists in the registry.

        Args:
            role: Role name

        Returns:
            True if role is valid, False otherwise
        """
        normalized_role = role.replace('-', '_')
        return normalized_role in self.models_config or normalized_role in self.FALLBACK_DEFAULTS

    def get_capability_deltas(self, role: str, provider: str) -> List[str]:
        """
        Identify capability gaps for a role on a specific provider.

        Compares role requirements (thinking, structured_output) with provider capabilities.

        Args:
            role: Role name
            provider: Provider name

        Returns:
            List of capability warnings (empty if fully compatible)
        """
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        provider_config = self.providers_config.get(provider)

        deltas = []

        if not role_config:
            deltas.append(f"Role '{role}' not found in registry")
            return deltas

        if not provider_config:
            deltas.append(f"Provider '{provider}' not found in registry")
            return deltas

        # Check thinking mode support
        if role_config.get('thinking', False) and not provider_config.get('thinking', False):
            deltas.append(
                f"Role requires extended thinking but provider '{provider}' doesn't support it"
            )

        # Check structured output support
        if role_config.get('structured_output', False) and not provider_config.get('structured_output', False):
            deltas.append(
                f"Role requires structured output but provider '{provider}' doesn't support it"
            )

        return deltas

    def list_all_roles(self) -> List[str]:
        """
        Get a list of all available roles.

        Returns:
            List of role names (in snake_case)
        """
        all_roles = set(self.models_config.keys())
        all_roles.update(self.FALLBACK_DEFAULTS.keys())
        return sorted(list(all_roles))

    def list_all_providers(self) -> List[str]:
        """
        Get a list of all available providers.

        Returns:
            List of provider names
        """
        return sorted(list(self.providers_config.keys()))

    def validate_all(self) -> Dict[str, Any]:
        """
        Validate entire registry for consistency.

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'coverage': {
                    'total_roles': int,
                    'roles_with_all_providers': int,
                    'roles_missing_providers': List[str],
                }
            }
        """
        errors = []
        warnings = []
        roles_with_all_providers = 0
        roles_missing_providers = []

        provider_list = self.list_all_providers()
        total_providers = len(provider_list)

        for role in self.list_all_roles():
            role_config = self.models_config.get(role)
            
            if not role_config:
                warnings.append(f"Role '{role}' only in defaults, not in models.yaml")
                continue

            # Check required fields
            if not role_config.get('canonical'):
                errors.append(f"Role '{role}' missing 'canonical' field")
            
            if 'thinking' not in role_config:
                errors.append(f"Role '{role}' missing 'thinking' field")
            
            if 'effort' not in role_config:
                errors.append(f"Role '{role}' missing 'effort' field")
            
            if not role_config.get('providers'):
                warnings.append(f"Role '{role}' has no provider mappings")
                roles_missing_providers.append(role)
                continue

            providers = role_config.get('providers', {})
            if len(providers) == total_providers:
                roles_with_all_providers += 1
            else:
                missing = set(provider_list) - set(providers.keys())
                warnings.append(
                    f"Role '{role}' missing providers: {', '.join(sorted(missing))}"
                )
                roles_missing_providers.append(role)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'coverage': {
                'total_roles': len(self.list_all_roles()),
                'roles_with_all_providers': roles_with_all_providers,
                'roles_missing_providers': roles_missing_providers,
            }
        }

    @staticmethod
    def from_defaults() -> 'ModelResolver':
        """
        Create a resolver with embedded defaults (no file needed).

        Returns:
            ModelResolver instance with fallback defaults
        """
        resolver = ModelResolver(fallback_to_defaults=True)
        logger.info("Created ModelResolver with embedded defaults")
        return resolver
