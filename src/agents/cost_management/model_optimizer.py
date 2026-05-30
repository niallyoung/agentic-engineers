"""
model_optimizer.py — Advanced Model Selection & Pareto Frontier Optimizer (COST-003)

Provides intelligent model selection with:
- Pareto frontier computation (O(n log n) dominant point detection)
- 5 recommendation types: cheapest, fastest, best quality, balanced, custom
- Mixed-model routing simulation and optimization
- Performance benchmarking (<100ms for 50 models)

Design principles:
- Pure in-memory computation, no I/O on hot paths
- All recommendations < 50ms
- Strict dominance for Pareto frontier (lower cost AND higher quality)
- Weighted tradeoff support for balanced recommendations

Usage:
    from src.agents.cost_management.model_optimizer import ModelOptimizer

    optimizer = ModelOptimizer()
    
    # Get Pareto frontier
    frontier = optimizer.get_pareto_frontier(
        task_type="code_review",
        input_tokens=5000,
        output_tokens=2000
    )
    
    # Get recommendations
    cheapest = optimizer.recommend_cheapest(task_type="general", input_tokens=1000, output_tokens=500)
    best_quality = optimizer.recommend_best_quality(task_type="code_review", input_tokens=5000, output_tokens=2000)
    balanced = optimizer.recommend_balanced(task_type="general", input_tokens=1000, output_tokens=500)
    
    # Simulate routing
    result = optimizer.simulate_model_mix({
        "claude-sonnet-4.5": 0.5,
        "claude-haiku-4.5": 0.3,
        "gpt-4o-mini": 0.2
    }, daily_tasks=1000, avg_tokens=(1000, 500))
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Metrics for a single model candidate."""
    model: str
    provider: str
    cost: float = 0.0
    quality: float = 0.0
    latency_sec: float = 0.0


@dataclass
class ParetoFrontier:
    """Result of Pareto frontier computation."""
    models: List[Dict[str, Any]] = field(default_factory=list)
    pareto_indices: List[int] = field(default_factory=list)
    computation_time_ms: float = 0.0
    total_models: int = 0


@dataclass
class RecommendationResult:
    """Result of model recommendation."""
    model: str
    provider: str
    estimated_cost: float
    estimated_quality: float
    estimated_latency_sec: float
    reasoning: str
    recommendation_type: str
    selection_time_ms: float


@dataclass
class RoutingSimulation:
    """Result of mixed-model routing simulation."""
    daily_cost: float
    avg_quality: float
    avg_latency_sec: float
    breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    simulation_time_ms: float = 0.0


class ModelOptimizer:
    """
    Advanced model selection optimizer with Pareto frontier computation
    and multiple recommendation strategies.
    
    Provides:
    - Pareto frontier computation O(n log n)
    - 5 recommendation types
    - Mixed-model routing simulation
    - Performance < 100ms for 50 models
    """
    
    def __init__(
        self,
        model_selector: Optional[Any] = None,
    ) -> None:
        """
        Initialize ModelOptimizer.
        
        Args:
            model_selector: Optional ModelSelector instance from dist/copilot/skills/model-selection
                          If not provided, will be lazy-loaded when needed.
        """
        self._selector = model_selector
    
    def _ensure_selector(self) -> Any:
        """Lazy-load ModelSelector if not provided."""
        if self._selector is None:
            try:
                # Try importing from the skill location
                import sys
                skill_root = Path(__file__).parent.parent.parent.parent / "dist" / "copilot" / "skills" / "model-selection"
                scripts_path = str(skill_root / "scripts")
                if scripts_path not in sys.path:
                    sys.path.insert(0, scripts_path)
                from model_selector import ModelSelector
                self._selector = ModelSelector()
                logger.debug("ModelSelector loaded from %s", scripts_path)
            except ImportError as e:
                logger.error("Failed to load ModelSelector: %s", e)
                raise RuntimeError("ModelSelector required but not available") from e
        return self._selector
    
    def get_pareto_frontier(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        providers: Optional[List[str]] = None,
    ) -> ParetoFrontier:
        """
        Compute the Pareto frontier (set of non-dominated models).
        
        A model is on the Pareto frontier if no other model is strictly better
        on all dimensions (lower cost AND higher quality).
        
        Algorithm: O(n log n) dominant point detection
        1. Sort models by cost ascending
        2. Scan left-to-right tracking max quality seen
        3. Models with increasing quality are non-dominated
        
        Args:
            task_type: Task category for quality estimation
            input_tokens: Expected input token count
            output_tokens: Expected output token count
            providers: Optional list of providers to filter by
        
        Returns:
            ParetoFrontier with models, pareto_indices, and computation time
        
        Performance: < 100ms for 50 models (typical case)
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        # Get all candidates
        result = selector.cost_quality_frontier(task_type, input_tokens, output_tokens, providers)
        models = result["models"]
        pareto_indices = result["pareto_indices"]
        
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return ParetoFrontier(
            models=models,
            pareto_indices=pareto_indices,
            computation_time_ms=elapsed_ms,
            total_models=len(models),
        )
    
    def recommend_cheapest(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Recommend the cheapest model.
        
        Args:
            task_type: Task category
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            constraints: Optional constraints dict
        
        Returns:
            RecommendationResult with cheapest model
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        constraints = constraints or {}
        
        # Recommend cheapest by setting very low max_cost doesn't work
        # Instead, manually find cheapest
        frontier = self.get_pareto_frontier(task_type, input_tokens, output_tokens)
        if not frontier.models:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return RecommendationResult(
                model="unknown", provider="unknown", estimated_cost=0.0,
                estimated_quality=0.0, estimated_latency_sec=0.0,
                reasoning="No models available", recommendation_type="cheapest",
                selection_time_ms=elapsed_ms,
            )
        
        cheapest = min(frontier.models, key=lambda m: m["estimated_cost"])
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return RecommendationResult(
            model=cheapest["model"],
            provider=cheapest["provider"],
            estimated_cost=cheapest["estimated_cost"],
            estimated_quality=cheapest["estimated_quality"],
            estimated_latency_sec=cheapest["estimated_latency_sec"],
            reasoning=f"Selected cheapest model: ${cheapest['estimated_cost']:.6f}",
            recommendation_type="cheapest",
            selection_time_ms=elapsed_ms,
        )
    
    def recommend_fastest(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Recommend the fastest model (minimum latency).
        
        Args:
            task_type: Task category
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            constraints: Optional constraints dict
        
        Returns:
            RecommendationResult with fastest model
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        frontier = self.get_pareto_frontier(task_type, input_tokens, output_tokens)
        if not frontier.models:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return RecommendationResult(
                model="unknown", provider="unknown", estimated_cost=0.0,
                estimated_quality=0.0, estimated_latency_sec=0.0,
                reasoning="No models available", recommendation_type="fastest",
                selection_time_ms=elapsed_ms,
            )
        
        fastest = min(frontier.models, key=lambda m: m["estimated_latency_sec"])
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return RecommendationResult(
            model=fastest["model"],
            provider=fastest["provider"],
            estimated_cost=fastest["estimated_cost"],
            estimated_quality=fastest["estimated_quality"],
            estimated_latency_sec=fastest["estimated_latency_sec"],
            reasoning=f"Selected fastest model: {fastest['estimated_latency_sec']:.2f}s latency",
            recommendation_type="fastest",
            selection_time_ms=elapsed_ms,
        )
    
    def recommend_best_quality(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Recommend the highest-quality model.
        
        Args:
            task_type: Task category
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            constraints: Optional constraints dict
        
        Returns:
            RecommendationResult with best quality model
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        frontier = self.get_pareto_frontier(task_type, input_tokens, output_tokens)
        if not frontier.models:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return RecommendationResult(
                model="unknown", provider="unknown", estimated_cost=0.0,
                estimated_quality=0.0, estimated_latency_sec=0.0,
                reasoning="No models available", recommendation_type="best_quality",
                selection_time_ms=elapsed_ms,
            )
        
        best = max(frontier.models, key=lambda m: m["estimated_quality"])
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return RecommendationResult(
            model=best["model"],
            provider=best["provider"],
            estimated_cost=best["estimated_cost"],
            estimated_quality=best["estimated_quality"],
            estimated_latency_sec=best["estimated_latency_sec"],
            reasoning=f"Selected best quality model: {best['estimated_quality']:.2f} quality score",
            recommendation_type="best_quality",
            selection_time_ms=elapsed_ms,
        )
    
    def recommend_balanced(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        cost_weight: float = 0.33,
        quality_weight: float = 0.33,
        latency_weight: float = 0.34,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Recommend a balanced model using weighted tradeoff.
        
        Uses a weighted scoring function:
        score = (1 - cost/max_cost) * cost_weight 
              + quality * quality_weight 
              - latency/max_latency * latency_weight
        
        Args:
            task_type: Task category
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            cost_weight: Weight for cost minimization (0-1)
            quality_weight: Weight for quality (0-1)
            latency_weight: Weight for latency minimization (0-1)
            constraints: Optional constraints dict
        
        Returns:
            RecommendationResult with balanced recommendation
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        frontier = self.get_pareto_frontier(task_type, input_tokens, output_tokens)
        if not frontier.models:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return RecommendationResult(
                model="unknown", provider="unknown", estimated_cost=0.0,
                estimated_quality=0.0, estimated_latency_sec=0.0,
                reasoning="No models available", recommendation_type="balanced",
                selection_time_ms=elapsed_ms,
            )
        
        models = frontier.models
        if not models:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
            return RecommendationResult(
                model="unknown", provider="unknown", estimated_cost=0.0,
                estimated_quality=0.0, estimated_latency_sec=0.0,
                reasoning="No models available", recommendation_type="balanced",
                selection_time_ms=elapsed_ms,
            )
        
        # Normalize weights
        total_weight = cost_weight + quality_weight + latency_weight
        cost_weight /= total_weight if total_weight > 0 else 1.0
        quality_weight /= total_weight if total_weight > 0 else 1.0
        latency_weight /= total_weight if total_weight > 0 else 1.0
        
        # Find min/max for normalization
        max_cost = max(m["estimated_cost"] for m in models) or 1.0
        max_latency = max(m["estimated_latency_sec"] for m in models) or 1.0
        
        best_model = None
        best_score = float("-inf")
        
        for model in models:
            cost_norm = 1.0 - (model["estimated_cost"] / max_cost) if max_cost > 0 else 1.0
            quality_norm = model["estimated_quality"]
            latency_norm = 1.0 - (model["estimated_latency_sec"] / max_latency) if max_latency > 0 else 1.0
            
            score = (cost_norm * cost_weight + 
                    quality_norm * quality_weight + 
                    latency_norm * latency_weight)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        if not best_model:
            best_model = models[0]
        
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return RecommendationResult(
            model=best_model["model"],
            provider=best_model["provider"],
            estimated_cost=best_model["estimated_cost"],
            estimated_quality=best_model["estimated_quality"],
            estimated_latency_sec=best_model["estimated_latency_sec"],
            reasoning=f"Balanced recommendation with weights: cost={cost_weight:.2f}, quality={quality_weight:.2f}, latency={latency_weight:.2f}",
            recommendation_type="balanced",
            selection_time_ms=elapsed_ms,
        )
    
    def recommend_custom(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        constraints: Dict[str, Any],
    ) -> RecommendationResult:
        """
        Recommend using custom constraints.
        
        Supports all constraints from ModelSelector.recommend_model():
        - max_cost (float)
        - quality_target (float)
        - max_latency_sec (float)
        - provider_preference (list)
        
        Args:
            task_type: Task category
            input_tokens: Expected input tokens
            output_tokens: Expected output tokens
            constraints: Custom constraints dict
        
        Returns:
            RecommendationResult
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        rec = selector.recommend_model(task_type, input_tokens, output_tokens, constraints)
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        return RecommendationResult(
            model=rec["model"],
            provider=rec["provider"],
            estimated_cost=rec["estimated_cost"],
            estimated_quality=rec["estimated_quality"],
            estimated_latency_sec=rec["estimated_latency_sec"],
            reasoning=rec["reasoning"],
            recommendation_type="custom",
            selection_time_ms=elapsed_ms,
        )
    
    def simulate_model_mix(
        self,
        mix: Dict[str, float],
        daily_tasks: int,
        avg_tokens: Tuple[int, int],
        task_type: str = "general",
    ) -> RoutingSimulation:
        """
        Simulate daily cost and quality for a hypothetical model mix.
        
        Args:
            mix: Dict mapping model_name → fraction (must sum to ~1.0)
            daily_tasks: Total tasks per day
            avg_tokens: Average (input_tokens, output_tokens) per task
            task_type: Task type for quality estimation
        
        Returns:
            RoutingSimulation with daily_cost, avg_quality, avg_latency, breakdown
        """
        start_ns = time.monotonic_ns()
        selector = self._ensure_selector()
        
        result = selector.simulate_model_mix(mix, daily_tasks, avg_tokens, task_type)
        
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000.0
        
        # Calculate average latency
        avg_latency = 0.0
        for model_name, fraction in mix.items():
            latency = selector._quality.get_avg_latency(model_name) / 1000.0  # Convert ms to seconds
            avg_latency += latency * fraction
        
        return RoutingSimulation(
            daily_cost=result["daily_cost"],
            avg_quality=result["avg_quality"],
            avg_latency_sec=avg_latency,
            breakdown=result["breakdown"],
            simulation_time_ms=elapsed_ms,
        )
