"""OpenAI provider adapter — GPT-4/GPT-5 models."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base_provider import BaseProvider


class OpenAIProvider(BaseProvider):
    """Cost adapter for OpenAI GPT-* models.

    Pricing source: https://openai.com/pricing (rates in providers.yaml)
    All costs are in USD per token.
    """

    PROVIDER_NAME = "openai"
    AUTH_ENV = "OPENAI_API_KEY"

    _BUILTIN_MODELS: Dict[str, Dict[str, float]] = {
        "gpt-5.5": {"input_per_1m": 12.00, "output_per_1m": 32.00},
        "gpt-5.4": {"input_per_1m": 6.00, "output_per_1m": 16.00},
        "gpt-5-mini": {"input_per_1m": 0.40, "output_per_1m": 1.60},
        "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
        "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
        "gpt-4-turbo": {"input_per_1m": 10.00, "output_per_1m": 30.00},
        "gpt-4": {"input_per_1m": 30.00, "output_per_1m": 60.00},
    }
    _BUILTIN_FALLBACK: Dict[str, float] = {"input_per_1m": 2.50, "output_per_1m": 10.00}

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        for model, rates in self._BUILTIN_MODELS.items():
            if model not in self._models:
                self._models[model] = rates
        if self._fallback == {"input_per_1m": 0.0, "output_per_1m": 0.0}:
            self._fallback = self._BUILTIN_FALLBACK.copy()

    def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API availability (env-var based, no network call)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        api_key = os.environ.get(self.AUTH_ENV, "")
        if api_key:
            return {"status": "healthy", "last_checked": now}
        return {
            "status": "unknown",
            "last_checked": now,
            "reason": f"{self.AUTH_ENV} not set",
        }
