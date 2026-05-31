#!/usr/bin/env python3
"""
cost_aggregator.py — Multi-Provider Cost Aggregation (COST-002)

Consolidates provider-specific AI costs into unified metrics, enabling
apples-to-apples cost comparison across Anthropic, OpenAI, Google Gemini,
GitHub Copilot, and Ollama (local/zero-cost).

Key design decisions:
- Provider pricing loaded from src/config/providers.yaml at runtime
- Provider adapters are pure-compute (no live API calls during cost calc)
- Health check results cached with configurable TTL (default 5 minutes)
- Usage records persisted to data_dir/{provider}/{YYYY-MM-DD}.json for trend queries
- aggregate_task_cost() completes in <10ms (no I/O in hot path)
- Graceful failover: if a provider's adapter fails, it's skipped (not fatal)

Usage:
    from scripts.cost_aggregator import CostAggregator

    agg = CostAggregator()

    # Compare cost across providers
    result = agg.aggregate_task_cost(
        task_type="code_review",
        input_tokens=5000,
        output_tokens=2000,
        model_variants={
            "anthropic": "claude-sonnet-4.6",
            "openai": "gpt-5.4",
            "google": "gemini-2.0",
            "copilot": "claude-sonnet-4.6",
            "ollama": "mistral:latest",
        }
    )
    # → {"anthropic": 0.045, "openai": 0.062, ..., "winner": "ollama", ...}
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .providers.anthropic_provider import AnthropicProvider
from .providers.openai_provider import OpenAIProvider
from .providers.google_provider import GoogleProvider
from .providers.copilot_provider import CopilotProvider
from .providers.ollama_provider import OllamaProvider
from .providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS = ("anthropic", "openai", "google", "copilot", "ollama")

#: ISO-8601 date format used for trend data file names and keys.
DATE_FMT = "%Y-%m-%d"

#: Minimum plausible cost that counts as "zero" for winner determination.
ZERO_COST_THRESHOLD = 1e-9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcdate(date_str: str) -> datetime:
    """Parse an ISO date string (YYYY-MM-DD) to UTC midnight datetime."""
    return datetime.strptime(date_str, DATE_FMT).replace(tzinfo=timezone.utc)


def _validate_date_str(date_str: str) -> str:
    """Validate and canonicalise an ISO ``YYYY-MM-DD`` date string.

    Guards against path traversal: ``date`` is used to build the on-disk
    record filename (``{date}.json``), so an unvalidated value such as
    ``"../../etc/passwd"`` would let a caller escape the data directory.
    Re-formatting via :func:`datetime.strptime`/``strftime`` guarantees the
    result contains only digits and hyphens in canonical form.

    Raises:
        ValueError: If *date_str* is not a valid ``YYYY-MM-DD`` date.
    """
    try:
        parsed = datetime.strptime(date_str, DATE_FMT)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid date '{date_str}'; expected format {DATE_FMT}"
        ) from exc
    return parsed.strftime(DATE_FMT)


def _date_range(start_date: str, end_date: str) -> List[str]:
    """Return list of YYYY-MM-DD strings from start_date to end_date (inclusive)."""
    start = _utcdate(start_date)
    end = _utcdate(end_date)
    if end < start:
        return []
    days = (end - start).days + 1
    return [(start + timedelta(days=i)).strftime(DATE_FMT) for i in range(days)]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class CostAggregator:
    """
    Aggregates and compares AI provider costs across Anthropic, OpenAI,
    Google Gemini, GitHub Copilot, and Ollama.

    Thread safety: cost calculations are stateless. Usage recording uses
    atomic write-then-rename for JSON persistence.
    """

    def __init__(
        self,
        providers_yaml: Optional[Path] = None,
        data_dir: Optional[Path] = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        """
        Args:
            providers_yaml:    Path to providers.yaml. Defaults to
                               src/config/providers.yaml relative to repo root.
            data_dir:          Directory for persisting usage records used by
                               cost_trend_for_provider(). Defaults to
                               ~/.copilot/cost-aggregation/.
            cache_ttl_seconds: TTL in seconds for provider_health_check() cache.
                               Default 300 (5 minutes).
        """
        self._providers_yaml = providers_yaml or self._find_providers_yaml()
        self._data_dir = Path(data_dir) if data_dir else Path.home() / ".copilot" / "cost-aggregation"
        self._cache_ttl = int(cache_ttl_seconds)

        self._providers_config: Dict[str, Any] = {}
        self._load_providers_config()

        self._adapters: Dict[str, BaseProvider] = self._init_adapters()

        # Health check cache
        self._health_cache: Dict[str, Any] = {}
        self._health_cache_ts: float = 0.0

        # Serialises the read-modify-write cycle in record_usage() so that
        # concurrent in-process writers to the same daily file do not lose
        # updates. (Cross-process safety still relies on atomic replace.)
        self._usage_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_providers_yaml() -> Path:
        """Locate providers.yaml relative to this file (up to repo root)."""
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "src" / "config" / "providers.yaml"
            if candidate.exists():
                return candidate
        # Fallback: cwd-relative
        candidate = Path("src") / "config" / "providers.yaml"
        if candidate.exists():
            return candidate.resolve()
        return here.parents[4] / "src" / "config" / "providers.yaml"

    def _load_providers_config(self) -> None:
        """Load provider pricing config from providers.yaml."""
        if not self._providers_yaml.exists():
            logger.warning(
                "providers.yaml not found at %s; using built-in rates only",
                self._providers_yaml,
            )
            return
        try:
            with open(self._providers_yaml, "r") as fh:
                data = yaml.safe_load(fh) or {}
            self._providers_config = data.get("providers", {})
            logger.debug(
                "Loaded cost config for %d providers", len(self._providers_config)
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to load providers.yaml: %s; using built-in rates", exc
            )

    def _init_adapters(self) -> Dict[str, BaseProvider]:
        """Instantiate all provider adapters with their config slices."""
        cfg = self._providers_config
        return {
            "anthropic": AnthropicProvider(cfg.get("anthropic", {})),
            "openai": OpenAIProvider(cfg.get("openai", {})),
            "google": GoogleProvider(cfg.get("google", {})),
            "copilot": CopilotProvider(cfg.get("copilot", {})),
            "ollama": OllamaProvider(cfg.get("ollama", {})),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate_task_cost(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        model_variants: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Compute and compare per-provider cost for a task.

        Args:
            task_type:      Descriptive label (e.g. "code_review"). Not used
                            in computation; stored in metadata only.
            input_tokens:   Number of input/prompt tokens.
            output_tokens:  Number of output/completion tokens.
            model_variants: Mapping of provider → model name. Only providers
                            listed here are included in the result.

        Returns:
            Dict with keys for each provider (cost in USD), plus:
            - ``winner``:                   Provider with lowest cost.
            - ``savings_vs_cheapest_cloud``: Savings vs. cheapest non-Ollama
                                            provider in USD.

        Example::

            agg.aggregate_task_cost(
                task_type="code_review",
                input_tokens=5000,
                output_tokens=2000,
                model_variants={
                    "anthropic": "claude-sonnet-4.6",
                    "openai": "gpt-5.4",
                    "google": "gemini-2.0",
                    "copilot": "claude-sonnet-4.6",
                    "ollama": "mistral:latest",
                }
            )
            # → {"anthropic": 0.045, "openai": 0.062, "google": 0.040,
            #    "copilot": 0.008, "ollama": 0.000,
            #    "winner": "ollama", "savings_vs_cheapest_cloud": 0.040}
        """
        t0 = time.monotonic()

        costs: Dict[str, float] = {}
        for provider, model in model_variants.items():
            adapter = self._adapters.get(provider)
            if adapter is None:
                logger.warning("Unknown provider '%s' — skipped", provider)
                continue
            try:
                costs[provider] = round(
                    adapter.calculate_cost(input_tokens, output_tokens, model), 8
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Provider '%s' calculate_cost failed: %s — skipped", provider, exc
                )

        # Determine winner (lowest cost)
        winner: Optional[str] = None
        if costs:
            winner = min(costs, key=lambda p: costs[p])

        # Savings vs cheapest *direct* cloud API provider.
        # "Cloud API providers" = anthropic, openai, google (raw per-token billing).
        # Excluded: ollama (local, zero-cost) and copilot (managed subscription service).
        _DIRECT_CLOUD = frozenset({"anthropic", "openai", "google"})
        cloud_costs = {p: c for p, c in costs.items() if p in _DIRECT_CLOUD}
        cheapest_cloud_cost = min(cloud_costs.values()) if cloud_costs else 0.0
        winner_cost = costs.get(winner, 0.0) if winner else 0.0
        savings = max(0.0, cheapest_cloud_cost - winner_cost)

        elapsed_ms = (time.monotonic() - t0) * 1000.0
        logger.debug(
            "aggregate_task_cost(%s): %d providers, winner=%s, elapsed=%.2fms",
            task_type,
            len(costs),
            winner,
            elapsed_ms,
        )

        return {**costs, "winner": winner, "savings_vs_cheapest_cloud": round(savings, 8)}

    def cost_trend_for_provider(
        self,
        provider: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Return daily spend trend for *provider* over the given date range.

        Usage data must have been recorded via :meth:`record_usage` for the
        dates requested; missing days default to 0.0.

        Args:
            provider:   Provider name (e.g. ``"anthropic"``).
            start_date: ISO date string ``"YYYY-MM-DD"`` (inclusive).
            end_date:   ISO date string ``"YYYY-MM-DD"`` (inclusive).

        Returns:
            ``{"daily_spend": [{"date": ..., "spend": ...}, ...],
               "total": float, "avg_per_day": float}``

        Raises:
            ValueError: If start_date > end_date or dates are unparsable.
        """
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Must be one of {SUPPORTED_PROVIDERS}."
            )

        try:
            dates = _date_range(start_date, end_date)
        except ValueError as exc:
            raise ValueError(f"Invalid date range: {exc}") from exc

        if not dates:
            raise ValueError(
                f"start_date '{start_date}' must be <= end_date '{end_date}'"
            )

        daily_spend: List[Dict[str, Any]] = []
        total = 0.0

        for date_str in dates:
            spend = self._load_daily_spend(provider, date_str)
            daily_spend.append({"date": date_str, "spend": round(spend, 6)})
            total += spend

        total = round(total, 6)
        avg_per_day = round(total / len(dates), 6) if dates else 0.0

        return {
            "provider": provider,
            "daily_spend": daily_spend,
            "total": total,
            "avg_per_day": avg_per_day,
        }

    def provider_health_check(self) -> Dict[str, Any]:
        """
        Return health status for all supported providers.

        Results are cached for ``cache_ttl_seconds`` (default 5 minutes) to
        avoid repeated env-var lookups on hot paths.

        Returns:
            ``{"anthropic": {"status": ..., "last_checked": ...}, ...}``
        """
        now = time.monotonic()
        if self._health_cache and (now - self._health_cache_ts) < self._cache_ttl:
            logger.debug("provider_health_check: returning cached result")
            return dict(self._health_cache)

        result: Dict[str, Any] = {}
        for provider_name, adapter in self._adapters.items():
            try:
                result[provider_name] = adapter.health_check()
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Health check failed for '%s': %s", provider_name, exc
                )
                result[provider_name] = {
                    "status": "unknown",
                    "reason": f"health check error: {exc}",
                }

        self._health_cache = result
        self._health_cache_ts = now
        logger.debug("provider_health_check: refreshed cache for %d providers", len(result))
        return dict(result)

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        date: Optional[str] = None,
        task_type: str = "unknown",
    ) -> None:
        """
        Record actual usage for cost trend tracking.

        Persists a usage record to ``data_dir/{provider}/{YYYY-MM-DD}.json``.
        Multiple calls on the same day are accumulated (summed).

        Args:
            provider:      Provider name (e.g. ``"anthropic"``).
            model:         Model name used for the call.
            input_tokens:  Number of input tokens consumed.
            output_tokens: Number of output tokens consumed.
            date:          ISO date string ``"YYYY-MM-DD"`` override.
                           Defaults to today (UTC).
            task_type:     Optional label for the task (stored in record).

        Raises:
            ValueError: If *provider* is not in SUPPORTED_PROVIDERS.
        """
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Must be one of {SUPPORTED_PROVIDERS}."
            )

        # Validate the date before it is used to build a file path, to prevent
        # path traversal via crafted values (e.g. "../../etc/cron").
        date_str = _validate_date_str(date) if date else _utcnow().strftime(DATE_FMT)
        adapter = self._adapters[provider]
        cost = adapter.calculate_cost(input_tokens, output_tokens, model)

        provider_dir = self._data_dir / provider
        record_path = provider_dir / f"{date_str}.json"

        # Serialise the load → accumulate → write cycle to avoid lost updates
        # when multiple threads record usage for the same provider/day.
        with self._usage_lock:
            provider_dir.mkdir(parents=True, exist_ok=True)

            # Load existing record (if any) and accumulate
            existing = self._load_json(record_path) or {}
            new_total = existing.get("total_spend", 0.0) + cost
            records = existing.get("records", [])
            records.append(
                {
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": round(cost, 8),
                    "task_type": task_type,
                    "recorded_at": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

            updated = {
                "provider": provider,
                "date": date_str,
                "total_spend": round(new_total, 8),
                "records": records,
            }
            self._write_json_atomic(record_path, updated)

    # ------------------------------------------------------------------
    # Convenience / introspection
    # ------------------------------------------------------------------

    def get_adapter(self, provider: str) -> BaseProvider:
        """Return the adapter for *provider*, raising KeyError if unknown."""
        if provider not in self._adapters:
            raise KeyError(
                f"No adapter for provider '{provider}'. "
                f"Supported: {list(self._adapters.keys())}"
            )
        return self._adapters[provider]

    def list_providers(self) -> List[str]:
        """Return list of supported provider names."""
        return list(self._adapters.keys())

    def invalidate_health_cache(self) -> None:
        """Force next call to provider_health_check() to re-query all providers."""
        self._health_cache = {}
        self._health_cache_ts = 0.0

    # ------------------------------------------------------------------
    # Internal I/O helpers
    # ------------------------------------------------------------------

    def _load_daily_spend(self, provider: str, date_str: str) -> float:
        """Return total spend for *provider* on *date_str* (0.0 if no record)."""
        record_path = self._data_dir / provider / f"{date_str}.json"
        data = self._load_json(record_path)
        if data is None:
            return 0.0
        return float(data.get("total_spend", 0.0))

    @staticmethod
    def _load_json(path: Path) -> Optional[dict]:
        """Load JSON from *path*; return None on any error."""
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _write_json_atomic(path: Path, data: dict) -> None:
        """Write *data* as JSON to *path* atomically (write-then-rename)."""
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(path)
        except OSError as exc:
            logger.error("Failed to write %s: %s", path, exc)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
