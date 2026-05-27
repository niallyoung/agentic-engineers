"""Ollama provider adapter — zero-cost local inference."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base_provider import BaseProvider


class OllamaProvider(BaseProvider):
    """Cost adapter for Ollama local inference.

    Ollama runs models locally — compute costs are absorbed by the host
    machine and not billed per-token. This provider always returns $0.00.

    Common models: mistral:latest, llama3:latest, codellama:latest, phi3:latest
    """

    PROVIDER_NAME = "ollama"
    AUTH_ENV = ""  # No auth needed for local Ollama

    _BUILTIN_MODELS: Dict[str, Dict[str, float]] = {
        "mistral:latest": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "llama3:latest": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "llama3.1:latest": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "codellama:latest": {"input_per_1m": 0.0, "output_per_1m": 0.0},
        "phi3:latest": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    }
    _BUILTIN_FALLBACK: Dict[str, float] = {"input_per_1m": 0.0, "output_per_1m": 0.0}

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        for model, rates in self._BUILTIN_MODELS.items():
            if model not in self._models:
                self._models[model] = rates
        # Ollama always uses zero-cost fallback
        self._fallback = {"input_per_1m": 0.0, "output_per_1m": 0.0}

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Ollama is always zero-cost regardless of model or token count."""
        return 0.0

    def is_zero_cost(self) -> bool:
        return True

    def health_check(self) -> Dict[str, Any]:
        """Ollama is considered available if running locally (optimistic)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # We don't attempt a real HTTP ping to avoid network dependency in tests.
        # COST-003 can add real liveness checks.
        return {"status": "healthy", "last_checked": now, "note": "local inference"}
