#!/usr/bin/env python3
"""
Canonical ModelResolver — the single source of truth for agent→model routing.

This module consolidates what were previously several scattered resolver
implementations into one canonical ``ModelResolver`` class. It reads
``src/config/models.yaml`` as the authoritative registry of role→model mappings,
provider-specific overrides, effort levels, and capability metadata.

Key guarantees:
- ``FALLBACK_DEFAULTS`` is DERIVED from ``models.yaml`` (not hardcoded), so it can
  never drift from the canonical registry. A test asserts the derived values match
  the canonical assignments.
- fable-5 is supported as a Security Engineer **defensive-only** alternative
  (see docs/SPEC.md > Security Engineer: Multi-Model Strategy). The default
  Security Engineer assignment is ``claude-opus-5``; fable-5 is only
  returned when the caller explicitly requests the defensive alternative.

Design: docs/architecture-model-centralization.md
"""

from __future__ import annotations

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
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Security Engineer defensive-only alternative (see docs/SPEC.md).
# The DEFAULT security_engineer assignment is claude-opus-5; fable-5 is only
# routed when the caller explicitly requests the defensive alternative.
FABLE_5_MODEL = "claude-fable-5"

# Roles that are not present in models.yaml's role_models but are still valid
# routing targets (aliases / framework-internal roles). They inherit a tier
# default. Kept minimal and explicit so list_all_roles stays meaningful.
_EXTRA_FALLBACK_ROLES: Dict[str, str] = {
    "orchestrator": "general_orchestrator",  # alias → derive from general_orchestrator
    "metrics": "engineer",                   # tier alias → haiku-class
    "testing": "engineer",                   # tier alias → haiku-class
    "spec_engineer": "lead_engineer",        # tier alias → sonnet-class
    "healing_engineer": "lead_engineer",     # tier alias → sonnet-class
    "spec_engineer_orchestrator": "lead_engineer",
}


class ValidationError(Exception):
    """Raised when model resolution validation fails."""
    pass


class ModelNotFoundError(Exception):
    """Raised when a role is not found in the registry."""
    pass


class ModelResolver:
    """
    Canonical resolver for role names to model names.

    Backed by ``src/config/models.yaml`` as the single source of truth.

    Supports:
    - Parsing models.yaml configuration
    - Converting between canonical and provider-specific formats
    - Environment-specific overrides (CLI > env vars > YAML > defaults)
    - Fallback strategies for missing providers or roles (derived from YAML)
    - Capability delta detection (thinking mode, structured output, etc.)
    - fable-5 defensive-only routing for the Security Engineer
    """

    # Provider used to derive the concrete fallback default model for each role.
    # "claude" is the canonical execution provider for the agentic-engineers
    # framework, so the fallback default for a role is its claude-provider model.
    _FALLBACK_PROVIDER = "claude"

    # Class-level cache of the derived defaults keyed by the resolved yaml path,
    # so FALLBACK_DEFAULTS is consistent and computed once per file.
    _fallback_cache: Dict[str, Dict[str, str]] = {}

    def __init__(self, models_yaml_path: Optional[str] = None, fallback_to_defaults: bool = True):
        """
        Initialize resolver from models.yaml file.

        Args:
            models_yaml_path: Path to models.yaml file. If None, auto-detects common locations.
            fallback_to_defaults: If True, use derived defaults if file not found and requested.

        Raises:
            FileNotFoundError: If models_yaml_path is specified but doesn't exist and
                              fallback_to_defaults is False.
        """
        self.fallback_to_defaults = fallback_to_defaults
        self.models_config: Dict[str, Any] = {}
        self.providers_config: Dict[str, Any] = {}
        self.models_yaml_path: Optional[Path] = None

        if models_yaml_path:
            path = Path(models_yaml_path)
        else:
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
            logger.warning("models.yaml not found, using derived defaults")

        # Derive FALLBACK_DEFAULTS from whatever role_models we loaded (or the
        # canonical file if we loaded nothing) so they can never drift.
        self.FALLBACK_DEFAULTS = self._derive_fallback_defaults()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @staticmethod
    def _find_models_yaml() -> Optional[Path]:
        """Auto-detect models.yaml in common locations (canonical first)."""
        candidates = [
            # Canonical location: src/config/models.yaml
            Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml",
            # Old root location (backwards compatibility)
            Path("models.yaml"),
            Path(__file__).resolve().parent.parent.parent.parent / "models.yaml",
            Path.home() / "git" / "agentic-engineers" / "src" / "config" / "models.yaml",
            Path.home() / "git" / "agentic-engineers" / "models.yaml",
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

    # ------------------------------------------------------------------
    # Derived fallback defaults (single source of truth — no hardcoding)
    # ------------------------------------------------------------------

    def _derive_fallback_defaults(self) -> Dict[str, str]:
        """
        Derive concrete per-role fallback default models from models.yaml.

        For each role in role_models, the fallback default is its canonical model
        (what resolve() returns when called with no provider argument).
        Extra alias roles (orchestrator, metrics, etc.) inherit the default of the role they alias.

        This is intentionally NOT hardcoded: the values are computed from the
        loaded registry so they can never disagree with the canonical config.
        """
        role_models = self.models_config
        if not role_models:
            # No registry loaded — derive from the canonical file directly so
            # from_defaults() still returns correct values.
            canonical_path = self._find_models_yaml()
            if canonical_path and canonical_path.exists():
                cache_key = str(canonical_path.resolve())
                if cache_key in self._fallback_cache:
                    return dict(self._fallback_cache[cache_key])
                with open(canonical_path, 'r') as f:
                    cfg = yaml.safe_load(f) or {}
                role_models = cfg.get('role_models', {})
            else:
                role_models = {}

        defaults: Dict[str, str] = {}
        for role, role_cfg in role_models.items():
            if not isinstance(role_cfg, dict):
                continue
            # Fallback default is the role's concrete claude-provider model
            # (e.g. "claude-haiku-4.5"), the version a real resolve() returns for
            # the default provider. Fall back to the short canonical alias only
            # when no claude provider entry exists. Deriving from providers.claude
            # keeps FALLBACK_DEFAULTS from drifting vs the canonical registry.
            providers = role_cfg.get('providers')
            model = None
            if isinstance(providers, dict):
                model = providers.get('claude')
            if not model:
                model = role_cfg.get('canonical')
            if model:
                defaults[role] = model

        # Add alias roles, inheriting from their target role.
        for alias, target in _EXTRA_FALLBACK_ROLES.items():
            if alias not in defaults and target in defaults:
                defaults[alias] = defaults[target]

        if self.models_yaml_path:
            self._fallback_cache[str(self.models_yaml_path.resolve())] = dict(defaults)
        return defaults

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        role: str,
        provider: Optional[str] = None,
        override: Optional[str] = None,
        defensive: bool = False,
    ) -> str:
        """
        Resolve a role name to a model name.

        Args:
            role: Role name (e.g., 'engineer', 'senior_engineer')
            provider: Provider context (e.g., 'copilot', 'claude', 'openai')
            override: Explicit override model name (highest precedence)
            defensive: For security_engineer only — when True, route to the
                fable-5 defensive-only alternative (see docs/SPEC.md). Ignored
                for all other roles. The default (False) preserves the canonical
                claude-opus-5 assignment.

        Returns:
            Model name (canonical or provider-specific equivalent)

        Raises:
            ModelNotFoundError: If role not found and not in fallback defaults
        """
        logger.debug(f"resolve(role={role}, provider={provider}, override={override}, defensive={defensive})")

        if override:
            return override

        normalized_role = role.replace('-', '_')

        # fable-5 defensive-only routing for the Security Engineer.
        if defensive and normalized_role == "security_engineer":
            logger.debug("security_engineer defensive request → fable-5")
            return FABLE_5_MODEL

        role_config = self.models_config.get(normalized_role)

        if not role_config:
            if self.fallback_to_defaults and normalized_role in self.FALLBACK_DEFAULTS:
                return self.FALLBACK_DEFAULTS[normalized_role]
            raise ModelNotFoundError(
                f"Role '{role}' not found in models.yaml and not in fallback defaults"
            )

        providers = role_config.get('providers', {})
        if provider:
            if provider in providers:
                return providers[provider]
            logger.debug(f"Provider {provider} not in models.yaml, falling back to default")

        # No (or unknown) provider: default to the concrete claude-provider model
        # (the framework's default harness), so a bare resolve(role) returns the
        # same versioned value as FALLBACK_DEFAULTS[role]. Fall back to the short
        # canonical alias only when no claude provider entry exists.
        claude_model = providers.get('claude')
        if claude_model:
            return claude_model

        canonical = role_config.get('canonical')
        if canonical:
            return canonical

        raise ValueError(f"Role {role} has no canonical model defined")

    def resolve_with_env(self, role: str, provider: Optional[str] = None) -> str:
        """
        Resolve with environment variable precedence.

        Precedence order:
        1. AGENT_MODEL_OVERRIDE_{ROLE}
        2. MODEL_TIER (haiku/sonnet/opus — applies to all agents)
        3. PREFERRED_PROVIDER
        4. models.yaml provider mapping
        5. models.yaml canonical
        """
        normalized_role = role.replace('-', '_').upper()

        override_key = f"AGENT_MODEL_OVERRIDE_{normalized_role}"
        if override_key in os.environ:
            return os.environ[override_key]

        tier = os.getenv("MODEL_TIER")
        if tier:
            model = self._resolve_tier_for_role(role, tier)
            if model:
                return model

        preferred_provider = os.getenv("PREFERRED_PROVIDER")
        if preferred_provider:
            provider = preferred_provider

        return self.resolve(role, provider=provider)

    def _resolve_tier_for_role(self, role: str, tier: str) -> Optional[str]:
        """Resolve a role to the canonical family for a given tier."""
        tier = tier.lower()
        tier_to_canonical = {
            'haiku': 'claude-haiku',
            'sonnet': 'claude-sonnet',
            'opus': 'claude-opus',
        }
        if tier not in tier_to_canonical:
            logger.warning(f"Unknown MODEL_TIER: {tier}")
            return None
        return tier_to_canonical[tier]

    # ------------------------------------------------------------------
    # Metadata accessors
    # ------------------------------------------------------------------

    def get_canonical(self, role: str) -> str:
        """Get the canonical (provider-independent) model for a role."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        canonical = role_config.get('canonical')
        if not canonical:
            raise ValueError(f"Role {role} has no canonical model defined")
        return canonical

    def get_effort(self, role: str) -> str:
        """Get the effort level for a role ('low'|'medium'|'high'|'max')."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        return role_config.get('effort', 'medium')

    def is_thinking_supported(self, role: str) -> bool:
        """Check if a role requires extended thinking mode."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        if not role_config:
            return False
        return role_config.get('thinking', False)

    def get_provider_specific(self, role: str, provider: str) -> Optional[str]:
        """Get provider-specific model name for a role (or None)."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        return role_config.get('providers', {}).get(provider)

    def get_all_providers(self, role: str) -> Dict[str, str]:
        """Get all provider-specific models for a role."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        if not role_config:
            raise ModelNotFoundError(f"Role '{role}' not found")
        return role_config.get('providers', {})

    def validate(self, role: str) -> bool:
        """Check if a role exists in the registry or fallback defaults."""
        normalized_role = role.replace('-', '_')
        return normalized_role in self.models_config or normalized_role in self.FALLBACK_DEFAULTS

    def get_capability_deltas(self, role: str, provider: str) -> List[str]:
        """Identify capability gaps for a role on a specific provider."""
        normalized_role = role.replace('-', '_')
        role_config = self.models_config.get(normalized_role)
        provider_config = self.providers_config.get(provider)

        deltas: List[str] = []
        if not role_config:
            deltas.append(f"Role '{role}' not found in registry")
            return deltas
        if not provider_config:
            deltas.append(f"Provider '{provider}' not found in registry")
            return deltas

        if role_config.get('thinking', False) and not provider_config.get('thinking', False):
            deltas.append(
                f"Role requires extended thinking but provider '{provider}' doesn't support it"
            )
        if role_config.get('structured_output', False) and not provider_config.get('structured_output', False):
            deltas.append(
                f"Role requires structured output but provider '{provider}' doesn't support it"
            )
        return deltas

    def list_all_roles(self) -> List[str]:
        """Get a sorted list of all available roles."""
        all_roles = set(self.models_config.keys())
        all_roles.update(self.FALLBACK_DEFAULTS.keys())
        return sorted(all_roles)

    def list_all_providers(self) -> List[str]:
        """Get a sorted list of all available providers."""
        return sorted(self.providers_config.keys())

    def validate_all(self) -> Dict[str, Any]:
        """Validate entire registry for consistency."""
        errors: List[str] = []
        warnings: List[str] = []
        roles_with_all_providers = 0
        roles_missing_providers: List[str] = []

        provider_list = self.list_all_providers()
        total_providers = len(provider_list)

        for role in self.list_all_roles():
            role_config = self.models_config.get(role)
            if not role_config:
                warnings.append(f"Role '{role}' only in defaults, not in models.yaml")
                continue

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
                warnings.append(f"Role '{role}' missing providers: {', '.join(sorted(missing))}")
                roles_missing_providers.append(role)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'coverage': {
                'total_roles': len(self.list_all_roles()),
                'roles_with_all_providers': roles_with_all_providers,
                'roles_missing_providers': roles_missing_providers,
            },
        }

    @classmethod
    def from_defaults(cls) -> 'ModelResolver':
        """Create a resolver, deriving defaults from the canonical models.yaml."""
        resolver = cls(fallback_to_defaults=True)
        logger.info("Created ModelResolver with derived defaults")
        return resolver
