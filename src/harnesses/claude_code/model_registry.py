"""
Model Registry for the Claude Code harness.

Model lifecycle registry for deprecation awareness. Tracks model status
(active, deprecated, alias) and provides canonical name resolution.

Usage::

    from src.harnesses.claude_code.model_registry import ModelRegistry

    registry = ModelRegistry()
    if registry.is_known("haiku"):
        canonical = registry.canonical("haiku")
        print(canonical)  # "claude-haiku-4.5"

    valid, warning = registry.validate("claude-sonnet-4.5")
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple


logger = logging.getLogger(__name__)


# Model registry with tier and status information.
MODEL_VERSIONS: Dict[str, Dict[str, str]] = {
    # Active full model names
    "claude-haiku-4.5": {"tier": "haiku", "status": "active"},
    "claude-sonnet-4.5": {"tier": "sonnet", "status": "active"},
    "claude-sonnet-4.6": {"tier": "sonnet", "status": "active"},
    "claude-opus-4.8": {"tier": "opus", "status": "active"},
    # Short aliases (backward compatibility)
    "claude-haiku-4-5": {"tier": "haiku", "status": "alias"},
    "haiku": {"tier": "haiku", "status": "alias"},
    "sonnet": {"tier": "sonnet", "status": "alias"},
    "opus": {"tier": "opus", "status": "alias"},
}


class ModelRegistry:
    """Registry for tracking model versions and deprecation status.

    Provides model validation, canonical name resolution, and tier lookup.
    """

    def __init__(self) -> None:
        """Initialize the model registry."""
        self._models = dict(MODEL_VERSIONS)

    def is_known(self, model: str) -> bool:
        """Check if a model is registered.

        Args:
            model: Model name or alias.

        Returns:
            True if model is in the registry.
        """
        return model in self._models

    def is_deprecated(self, model: str) -> bool:
        """Check if a model is deprecated.

        Args:
            model: Model name or alias.

        Returns:
            True if model status is "deprecated".
        """
        if not self.is_known(model):
            return False
        return self._models[model].get("status") == "deprecated"

    def canonical(self, model: str) -> Optional[str]:
        """Resolve a model alias to its canonical (full) name.

        For non-alias models, returns the input unchanged. For aliases,
        resolves to the matching full model name.

        Args:
            model: Model name or alias.

        Returns:
            Canonical model name, or None if not found.

        Examples:
            canonical("haiku") -> "claude-haiku-4.5"
            canonical("claude-sonnet-4.5") -> "claude-sonnet-4.5"
        """
        if not self.is_known(model):
            return None

        status = self._models[model].get("status")

        # If it's an alias, find the corresponding active model
        if status == "alias":
            tier = self._models[model].get("tier")
            for candidate, meta in self._models.items():
                if (meta.get("status") == "active" and
                    meta.get("tier") == tier):
                    return candidate
            # Fallback if no active model found
            return None

        # Non-alias models return themselves
        return model

    def tier(self, model: str) -> Optional[str]:
        """Get the tier (complexity class) of a model.

        Args:
            model: Model name or alias.

        Returns:
            Tier string ("haiku", "sonnet", "opus"), or None if not found.
        """
        if not self.is_known(model):
            return None
        return self._models[model].get("tier")

    def validate(self, model: str) -> Tuple[bool, Optional[str]]:
        """Validate a model name and return status.

        Args:
            model: Model name or alias to validate.

        Returns:
            Tuple of (valid, warning_msg). valid is True if model is known
            and not deprecated. warning_msg describes any issues found.
        """
        if not self.is_known(model):
            return False, f"Model '{model}' not recognized."

        if self.is_deprecated(model):
            canonical = self.canonical(model)
            msg = (
                f"Model '{model}' is deprecated. "
                f"Please use '{canonical}' instead."
            )
            return False, msg

        status = self._models[model].get("status")
        if status == "alias":
            canonical = self.canonical(model)
            msg = (
                f"Using alias '{model}'; resolves to '{canonical}'."
            )
            return True, msg

        # Active, full model name
        return True, None
