"""
model_selector.py — Model Selection Optimization (COST-003)

Recommends optimal models for tasks given budget constraints, quality targets,
and latency requirements.  Uses provider cost rates from src/config/models.yaml
and quality heuristics from QualityEstimator.

Design decisions:
- Cost calculation mirrors COST-001 (CostBudgeter.calculate_provider_cost)
- Optionally accepts a CostAggregator from COST-002 when available
- All recommendations are made in < 50 ms (pure in-memory, no I/O on hot path)
- Pareto frontier: strict dominance (lower cost AND higher quality)

Usage:
    from src.skills.model_selection.scripts.model_selector import ModelSelector

    selector = ModelSelector()
    rec = selector.recommend_model(
        task_type="code_review",
        input_tokens=5000,
        output_tokens=2000,
        constraints={
            "max_cost": 0.10,
            "quality_target": 0.85,
            "max_latency_sec": 5.0,
            "provider_preference": ["anthropic", "ollama", "openai"],
        },
    )
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from scripts.quality_estimator import QualityEstimator

logger = logging.getLogger(__name__)

# Fallback per-1K-token rates (USD) when models.yaml is missing
_FALLBACK_RATES: Dict[str, float] = {"input": 0.0025, "output": 0.01}

_DEFAULT_PROVIDER_ORDER = ["anthropic", "openai", "google", "ollama"]


@dataclass
class _ModelInfo:
    """Internal representation of a candidate model."""
    model: str
    provider: str
    cost: float = 0.0
    quality: float = 0.0
    latency_sec: float = 0.0


class ModelSelector:
    """
    Recommends optimal models for tasks given cost/quality/latency constraints.

    Loads provider cost rates and model metadata from src/config/models.yaml.
    Accepts an optional ``cost_aggregator`` (COST-002) for richer cost data.

    Thread safety: read-only after __init__; safe to call from multiple threads.
    """

    def __init__(
        self,
        models_yaml: Optional[Path] = None,
        cost_aggregator: Optional[Any] = None,
        quality_estimator: Optional[Any] = None,
    ) -> None:
        """
        Args:
            models_yaml:      Path override for models.yaml.
            cost_aggregator:  Optional COST-002 CostAggregator instance.
                              When provided, its ``aggregate_task_cost``
                              method is called for cost estimates.
            quality_estimator: Optional pre-initialized QualityEstimator.
                               If not provided, creates its own.
        """
        self._yaml_path = models_yaml or self._find_models_yaml()
        self._cost_aggregator = cost_aggregator
        self._provider_rates: Dict[str, Dict] = {}
        self._model_meta: Dict[str, Dict] = {}
        self._load_config()
        self._quality = quality_estimator or QualityEstimator(models_yaml=self._yaml_path)

    def _find_models_yaml(self) -> Optional[Path]:
        """Locate src/config/models.yaml relative to this file."""
        here = Path(__file__).parent
        for _ in range(4):
            candidate = here / "src" / "config" / "models.yaml"
            if candidate.exists():
                return candidate
            here = here.parent
        return None

    def _load_config(self) -> None:
        """Load provider rates and model metadata from models.yaml."""
        if not self._yaml_path or not Path(self._yaml_path).exists():
            logger.warning("models.yaml not found at %s; using fallback rates", self._yaml_path)
            return
        try:
            with open(self._yaml_path) as fh:
                data = yaml.safe_load(fh) or {}
            self._provider_rates = data.get("providers", {})
            sel = data.get("model_selection", {})
            self._model_meta = sel.get("models", {})
            logger.debug("Loaded %d providers, %d model entries", len(self._provider_rates), len(self._model_meta))
        except Exception as exc:
            logger.warning("Failed to load models.yaml: %s; using fallback rates", exc)

    def _resolve_rates(self, provider: str, model: str) -> Dict[str, float]:
        """Return per-1K-token USD rates for (provider, model) with fallback."""
        provider_rates = self._provider_rates.get(provider, {})
        rates = provider_rates.get(model)
        if rates:
            return rates
        # Try partial match on model name
        for key, r in provider_rates.items():
            if key in model or model in key:
                return r
        
        # Try to get rates from QualityEstimator's config
        if self._quality and self._quality.config.get("models", {}).get(model):
            model_config = self._quality.config["models"][model]
            if "rates" in model_config:
                return model_config["rates"]
        
        return _FALLBACK_RATES

    def _calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_type: str = "general",
    ) -> float:
        """Compute USD cost for a token pair using CostAggregator (COST-002) or built-in rates."""
        if self._cost_aggregator is not None:
            try:
                result = self._cost_aggregator.aggregate_task_cost(
                    task_type, input_tokens, output_tokens, model_variants={provider: model}
                )
                cost = result.get(provider)
                if cost is not None:
                    return float(cost)
            except Exception as exc:
                logger.debug("CostAggregator failed for %s/%s: %s; falling back to rates", provider, model, exc)
        rates = self._resolve_rates(provider, model)
        return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1000.0

    def _all_models(self) -> List[_ModelInfo]:
        """Return a list of all known models with empty cost/quality fields."""
        result = []
        seen = set()
        
        # First, try to get models from loaded config
        models_dict = self._model_meta
        
        # If no models in config, try to get from QualityEstimator
        if not models_dict and self._quality:
            models_list = self._quality.list_known_models()
            for model_name in models_list:
                tier = self._quality.get_model_tier(model_name)
                latency = self._quality.get_avg_latency(model_name)
                if model_name not in seen:
                    seen.add(model_name)
                    result.append(_ModelInfo(
                        model=model_name,
                        provider="unknown",  # Don't know provider from tier
                        latency_sec=latency / 1000.0,  # convert ms to seconds
                    ))
            return result
        
        for model_name, meta in models_dict.items():
            if model_name in seen:
                continue
            seen.add(model_name)
            result.append(_ModelInfo(
                model=model_name,
                provider=meta.get("provider", "unknown"),
                latency_sec=float(meta.get("avg_latency_sec", 3.0)),
            ))
        return result

    def _enrich_models(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        provider_filter: Optional[List[str]] = None,
    ) -> List[_ModelInfo]:
        """
        Return a list of fully-enriched _ModelInfo objects (cost + quality) for
        all models that belong to the requested providers.
        """
        candidates = self._all_models()
        if provider_filter:
            candidates = [c for c in candidates if c.provider in provider_filter]
        for info in candidates:
            info.cost = self._calculate_cost(info.provider, info.model, input_tokens, output_tokens, task_type)
            info.quality = self._quality.estimate_quality(info.model, task_type)
        return candidates

    @staticmethod
    def _sort_key_best_quality(info: _ModelInfo) -> Tuple[float, float]:
        """Sort by quality descending, then cost ascending (for tie-breaking)."""
        return (-info.quality, info.cost)

    def recommend_model(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Recommend the best model for a task given budget/quality/latency constraints.

        Args:
            task_type:     Task category (e.g. 'code_review', 'documentation').
            input_tokens:  Expected input token count.
            output_tokens: Expected output token count.
            constraints:   Optional dict with keys:
                             max_cost (float)           — max USD per task
                             quality_target (float)     — minimum quality score [0,1]
                             max_latency_sec (float)    — max acceptable latency
                             provider_preference (list) — ordered provider list

        Returns:
            Dict with keys: model, provider, estimated_cost, estimated_quality,
            estimated_latency_sec, reasoning, _selection_time_ms.
        """
        start_ns = time.monotonic_ns()
        constraints = constraints or {}
        max_cost = constraints.get("max_cost")
        quality_target = constraints.get("quality_target")
        provider_pref = constraints.get("provider_preference") or []

        # Build candidate set — try preferred providers first, fall back to all
        provider_filter = list(provider_pref) if provider_pref else None
        candidates = self._enrich_models(task_type, input_tokens, output_tokens, provider_filter)
        if not candidates and provider_filter:
            candidates = self._enrich_models(task_type, input_tokens, output_tokens)

        if not candidates:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return {
                "model": "unknown",
                "provider": "unknown",
                "estimated_cost": 0.0,
                "estimated_quality": 0.0,
                "estimated_latency_sec": 0.0,
                "reasoning": "No models available",
                "_selection_time_ms": round(elapsed_ms, 6),
            }

        reasons: List[str] = []

        # Apply latency constraint
        max_latency = constraints.get("max_latency_sec")
        if max_latency is not None:
            fast_enough = [c for c in candidates if c.latency_sec <= max_latency]
            if not fast_enough:
                best = min(candidates, key=lambda c: c.latency_sec)
                elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
                return {
                    "model": best.model,
                    "provider": best.provider,
                    "estimated_cost": round(best.cost, 6),
                    "estimated_quality": best.quality,
                    "estimated_latency_sec": best.latency_sec,
                    "reasoning": f"No model meets latency SLA ({max_latency}s); using fastest available",
                    "_selection_time_ms": round(elapsed_ms, 6),
                }
            candidates = fast_enough

        # Apply cost constraint
        under_budget = candidates
        if max_cost is not None:
            under_budget = [c for c in candidates if c.cost <= max_cost]
            if not under_budget:
                cheapest = min(candidates, key=lambda c: c.cost)
                elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
                return {
                    "model": cheapest.model,
                    "provider": cheapest.provider,
                    "estimated_cost": round(cheapest.cost, 6),
                    "estimated_quality": cheapest.quality,
                    "estimated_latency_sec": cheapest.latency_sec,
                    "reasoning": f"All models exceed max_cost=${max_cost}; cheapest option selected ({cheapest.model})",
                    "_selection_time_ms": round(elapsed_ms, 6),
                }
            candidates = under_budget
            reasons.append(f"Best quality within budget")

        # Sort by quality (desc), then cost (asc)
        candidates = sorted(candidates, key=self._sort_key_best_quality)

        # Apply quality target
        if quality_target is not None:
            feasible = [c for c in candidates if c.quality >= quality_target]
            if not feasible:
                best = candidates[0]
                reasons.append(f"Quality target {quality_target} not achievable; best available is {best.quality:.2f}")
            else:
                best = feasible[0]
        else:
            best = candidates[0]

        # Provider fallback advisory
        if provider_pref and best.provider not in provider_pref:
            reasons.append(f"{provider_pref} unavailable or over budget")

        if not reasons:
            reasons.append("Constraint relaxed: returning best available")

        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        return {
            "model": best.model,
            "provider": best.provider,
            "estimated_cost": round(best.cost, 6),
            "estimated_quality": best.quality,
            "estimated_latency_sec": best.latency_sec,
            "reasoning": "; ".join(reasons),
            "_selection_time_ms": round(elapsed_ms, 6),
        }

    def recommend_batch(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Recommend models for multiple tasks in one call.

        Args:
            tasks: List of task specs, each with keys:
                     task_type (str)
                     tokens (tuple[int, int])   – (input_tokens, output_tokens)
                     constraints (dict)         – same keys as recommend_model
        Returns:
            List of recommendation dicts, each with all recommend_model keys
            plus 'task_type' and '_cumulative_cost'.
        """
        results = []
        cumulative = 0.0
        for task in tasks:
            task_type = task.get("task_type", "general")
            tokens = task.get("tokens", (0, 0))
            in_tok, out_tok = int(tokens[0]), int(tokens[1])
            constraints = task.get("constraints", {})
            rec = self.recommend_model(task_type, in_tok, out_tok, constraints)
            cumulative += rec.get("estimated_cost", 0.0)
            rec["task_type"] = task_type
            rec["_cumulative_cost"] = round(cumulative, 6)
            results.append(rec)
        return results

    def cost_quality_frontier(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        providers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compute the cost-quality Pareto frontier for a task.

        A model is on the Pareto frontier if no other model is both cheaper
        AND higher quality (strict dominance on at least one dimension).

        Args:
            task_type:     Task category.
            input_tokens:  Input token count.
            output_tokens: Output token count.
            providers:     Optional list of providers to include.

        Returns:
            Dict with keys:
                models: list of model dicts sorted by cost ascending
                pareto_indices: indices (into models list) of non-dominated models
        """
        provider_filter = providers if providers else None
        models_list = self._enrich_models(task_type, input_tokens, output_tokens, provider_filter)
        # Sort by cost ascending
        models_list = sorted(models_list, key=lambda c: (c.cost, -c.quality))

        n = len(models_list)
        pareto_indices = []
        for i in range(n):
            dominated = False
            for j in range(n):
                if i == j:
                    continue
                ci, cj = models_list[i], models_list[j]
                # j dominates i if j is cheaper-or-equal AND better-or-equal quality, strict on at least one
                if cj.cost <= ci.cost and cj.quality >= ci.quality and (cj.cost < ci.cost or cj.quality > ci.quality):
                    dominated = True
                    break
            if not dominated:
                pareto_indices.append(i)

        model_dicts = [
            {
                "model": m.model,
                "provider": m.provider,
                "estimated_cost": round(m.cost, 6),
                "estimated_quality": m.quality,
                "estimated_latency_sec": m.latency_sec,
            }
            for m in models_list
        ]
        return {"models": model_dicts, "pareto_indices": pareto_indices}

    def simulate_model_mix(
        self,
        mix: Dict[str, float],
        daily_tasks: int,
        avg_tokens: Tuple[int, int],
        task_type: str = "general",
    ) -> Dict[str, Any]:
        """
        Predict daily cost and average quality for a hypothetical model mix.

        Args:
            mix:         Dict mapping model_name → fraction of tasks (must sum to ~1.0).
            daily_tasks: Total tasks per day.
            avg_tokens:  Average (input_tokens, output_tokens) per task.
            task_type:   Task type for quality estimation.

        Returns:
            Dict with keys: daily_cost, avg_quality, breakdown.
        """
        in_tok, out_tok = int(avg_tokens[0]), int(avg_tokens[1])
        total_fraction = sum(mix.values())
        if abs(total_fraction - 1.0) > 0.01:
            logger.warning("Model mix fractions sum to %.3f (expected 1.0); normalising", total_fraction)
            mix = {k: v / total_fraction for k, v in mix.items()}

        daily_cost = 0.0
        weighted_quality = 0.0
        breakdown: Dict[str, Any] = {}

        for model_name, fraction in mix.items():
            meta = self._model_meta.get(model_name, {})
            provider = meta.get("provider", "unknown")
            cost_per_task = self._calculate_cost(provider, model_name, in_tok, out_tok, task_type)
            quality = self._quality.estimate_quality(model_name, task_type)
            tasks_this_model = daily_tasks * fraction
            model_daily_cost = cost_per_task * tasks_this_model
            daily_cost += model_daily_cost
            weighted_quality += quality * fraction
            breakdown[model_name] = {
                "fraction": fraction,
                "cost_per_task": round(cost_per_task, 6),
                "daily_cost": round(model_daily_cost, 4),
                "quality": quality,
                "provider": provider,
            }

        return {
            "daily_cost": round(daily_cost, 4),
            "avg_quality": round(weighted_quality, 4),
            "breakdown": breakdown,
        }
