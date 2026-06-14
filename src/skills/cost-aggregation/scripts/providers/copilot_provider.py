"""GitHub Copilot provider adapter — per-use pricing model."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base_provider import BaseProvider


class CopilotProvider(BaseProvider):
    """Cost adapter for GitHub Copilot.

    GitHub Copilot uses a per-use pricing model significantly cheaper than
    direct API access. Rates are estimated based on Copilot API documentation.

    Pricing source: GitHub Copilot API pricing (rates in providers.yaml)
    """

    PROVIDER_NAME = "copilot"
    AUTH_ENV = "GITHUB_TOKEN"

    _BUILTIN_MODELS: Dict[str, Dict[str, float]] = {
        "claude-sonnet-4.6": {"input_per_1m": 1.00, "output_per_1m": 1.50},
        "claude-sonnet-4.5": {"input_per_1m": 1.00, "output_per_1m": 1.50},
        "claude-haiku-4.5": {"input_per_1m": 0.20, "output_per_1m": 0.40},
        "claude-opus-4.8": {"input_per_1m": 2.00, "output_per_1m": 4.00},
        "claude-opus-4.6": {"input_per_1m": 2.00, "output_per_1m": 4.00},
        "gpt-4o": {"input_per_1m": 0.80, "output_per_1m": 1.20},
        "gpt-4o-mini": {"input_per_1m": 0.10, "output_per_1m": 0.20},
    }
    _BUILTIN_FALLBACK: Dict[str, float] = {"input_per_1m": 1.00, "output_per_1m": 1.50}

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        for model, rates in self._BUILTIN_MODELS.items():
            if model not in self._models:
                self._models[model] = rates
        if self._fallback == {"input_per_1m": 0.0, "output_per_1m": 0.0}:
            self._fallback = self._BUILTIN_FALLBACK.copy()

    def health_check(self) -> Dict[str, Any]:
        """Check GitHub Copilot API availability (env-var based, no network call)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        token = os.environ.get(self.AUTH_ENV, "")
        if token:
            return {"status": "healthy", "last_checked": now}
        return {
            "status": "unknown",
            "last_checked": now,
            "reason": "no API access",
        }
