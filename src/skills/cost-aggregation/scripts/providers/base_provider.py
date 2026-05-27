"""Base provider interface for cost aggregation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseProvider(ABC):
    """Abstract base class for all cost provider adapters."""

    #: Name used in provider_health_check results and log messages.
    PROVIDER_NAME: str = "unknown"

    #: Environment variable that holds this provider's auth credential.
    AUTH_ENV: str = ""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Args:
            config: Provider-specific section from providers.yaml
                    (already sliced, not the full file).
        """
        self._config = config
        self._models: Dict[str, Dict[str, float]] = {}
        self._fallback: Dict[str, float] = {"input_per_1m": 0.0, "output_per_1m": 0.0}
        self._load_config(config)

    def _load_config(self, config: Dict[str, Any]) -> None:
        """Parse provider config dict into internal model rate tables."""
        self._models = {
            name: {
                "input_per_1m": float(rates.get("input_per_1m", 0.0)),
                "output_per_1m": float(rates.get("output_per_1m", 0.0)),
            }
            for name, rates in config.get("models", {}).items()
            if isinstance(rates, dict)
        }
        fallback = config.get("fallback", {})
        if fallback:
            self._fallback = {
                "input_per_1m": float(fallback.get("input_per_1m", 0.0)),
                "output_per_1m": float(fallback.get("output_per_1m", 0.0)),
            }

    def get_rates(self, model: str) -> Dict[str, float]:
        """Return (input_per_1m, output_per_1m) rates for *model*, or fallback."""
        return self._models.get(model, self._fallback)

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Compute USD cost for *input_tokens* + *output_tokens* using *model* rates.

        Returns:
            Cost in USD (never negative).
        """
        rates = self.get_rates(model)
        cost = (
            input_tokens * rates["input_per_1m"]
            + output_tokens * rates["output_per_1m"]
        ) / 1_000_000.0
        return max(0.0, cost)

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return a health status dict for this provider."""
        ...

    def is_zero_cost(self) -> bool:
        """Return True if this provider is always zero-cost (e.g., Ollama)."""
        return self._config.get("zero_cost", False)

    def known_models(self) -> list:
        """Return list of model names this provider has explicit pricing for."""
        return list(self._models.keys())
