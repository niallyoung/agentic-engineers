"""Anthropic provider adapter — claude-* models."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    """Cost adapter for Anthropic claude-* models.

    Pricing source: https://www.anthropic.com/api (rates in providers.yaml)
    All costs are in USD per token.
    """

    PROVIDER_NAME = "anthropic"
    AUTH_ENV = "ANTHROPIC_API_KEY"

    # Hardcoded baseline rates (fallback if providers.yaml missing/empty)
    _BUILTIN_MODELS: Dict[str, Dict[str, float]] = {
        "claude-sonnet-4.6": {"input_per_1m": 3.00, "output_per_1m": 15.00},
        "claude-sonnet-4.5": {"input_per_1m": 3.00, "output_per_1m": 15.00},
        "claude-haiku-4.5": {"input_per_1m": 0.25, "output_per_1m": 1.25},
        "claude-opus-4.7": {"input_per_1m": 15.00, "output_per_1m": 75.00},
        "claude-3-5-sonnet-20241022": {"input_per_1m": 3.00, "output_per_1m": 15.00},
        "claude-3-haiku-20240307": {"input_per_1m": 0.25, "output_per_1m": 1.25},
        "claude-3-opus-20240229": {"input_per_1m": 15.00, "output_per_1m": 75.00},
    }
    _BUILTIN_FALLBACK: Dict[str, float] = {"input_per_1m": 3.00, "output_per_1m": 15.00}

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        # Merge builtin rates for models not in providers.yaml
        for model, rates in self._BUILTIN_MODELS.items():
            if model not in self._models:
                self._models[model] = rates
        # Ensure fallback is reasonable
        if self._fallback == {"input_per_1m": 0.0, "output_per_1m": 0.0}:
            self._fallback = self._BUILTIN_FALLBACK.copy()

    def health_check(self) -> Dict[str, Any]:
        """Check Anthropic API availability (env-var based, no network call)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        api_key = os.environ.get(self.AUTH_ENV, "")
        if api_key:
            return {"status": "healthy", "last_checked": now}
        return {
            "status": "unknown",
            "last_checked": now,
            "reason": f"{self.AUTH_ENV} not set",
        }
