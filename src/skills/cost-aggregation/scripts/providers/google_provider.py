"""Google Gemini provider adapter."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from .base_provider import BaseProvider


class GoogleProvider(BaseProvider):
    """Cost adapter for Google Gemini models.

    Pricing source: https://ai.google.dev/pricing (rates in providers.yaml)
    All costs are in USD per token.
    """

    PROVIDER_NAME = "google"
    AUTH_ENV = "GOOGLE_API_KEY"

    _BUILTIN_MODELS: Dict[str, Dict[str, float]] = {
        "gemini-2.0": {"input_per_1m": 6.00, "output_per_1m": 5.00},
        "gemini-2.0-flash": {"input_per_1m": 0.075, "output_per_1m": 0.30},
        "gemini-2.0-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00},
        "gemini-2-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00},
        "gemini-1-5-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00},
        "gemini-1.5-flash": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    }
    _BUILTIN_FALLBACK: Dict[str, float] = {"input_per_1m": 1.25, "output_per_1m": 5.00}

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        for model, rates in self._BUILTIN_MODELS.items():
            if model not in self._models:
                self._models[model] = rates
        if self._fallback == {"input_per_1m": 0.0, "output_per_1m": 0.0}:
            self._fallback = self._BUILTIN_FALLBACK.copy()

    def health_check(self) -> Dict[str, Any]:
        """Check Google Gemini API availability (env-var based, no network call)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        api_key = os.environ.get(self.AUTH_ENV, "")
        if api_key:
            return {"status": "healthy", "last_checked": now}
        return {
            "status": "unknown",
            "last_checked": now,
            "reason": f"{self.AUTH_ENV} not set",
        }
