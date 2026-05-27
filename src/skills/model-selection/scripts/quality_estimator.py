"""
quality_estimator.py — Quality estimation helper for COST-003 (ModelSelector)

Predicts task quality scores for each model based on:
- Model tier (haiku / sonnet / opus / mini)
- Task type (code_review, security_audit, documentation, general, …)
- Per-task-type tier adjustments loaded from models.yaml

Quality scores are in [0.0, 1.0]:
  - 0.55–0.70  fast / budget models (haiku-class, mini-class)
  - 0.75–0.90  balanced models (sonnet-class)
  - 0.90–0.99  premium models (opus-class)

Scores are clamped to [0.0, 1.0] after applying task-type adjustments.

Usage:
    from scripts.quality_estimator import QualityEstimator

    qe = QualityEstimator()
    score = qe.estimate_quality("claude-sonnet-4.6", "code_review")  # → 0.90
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Fallback quality by tier when models.yaml is unavailable
_FALLBACK_TIER_QUALITY: Dict[str, float] = {
    "mini": 0.62,
    "haiku": 0.65,
    "sonnet": 0.82,
    "opus": 0.95,
}

# Fallback latency (ms) by tier when models.yaml is unavailable
_FALLBACK_TIER_LATENCY: Dict[str, float] = {
    "mini": 300,      # fast models
    "haiku": 200,     # very fast
    "sonnet": 500,    # moderate
    "opus": 800,      # slower, more powerful
    "local": 1000,    # local/ollama models are slower
}

# Keywords per tier — checked against dash-split parts of model name
# Order matters: checked left-to-right, first match wins
# Tier names (mini, haiku, sonnet, opus) have higher priority than model keywords
_TIER_KEYWORDS: Dict[str, str] = {
    "opus": "opus",
    "sonnet": "sonnet",
    "haiku": "haiku",
    "mini": "mini",
    "local": "local",
    # Model-specific keywords (lower priority)
    "4o": "sonnet",      # gpt-4o (OpenAI sonnet-class)
    "turbo": "sonnet",   # gpt-4-turbo → sonnet tier
    "pro": "sonnet",     # gemini-pro → sonnet tier
    "flash": "haiku",    # gemini flash → haiku tier
}


def _infer_tier(model_name: str) -> str:
    """Infer quality tier from model name by matching dash-separated parts."""
    parts = set(model_name.replace(".", "-").split("-"))
    for keyword, tier in _TIER_KEYWORDS.items():
        if keyword in parts:
            return tier
    # fallback substring scan for names like "gpt-4o" (no dash-part match)
    for keyword, tier in _TIER_KEYWORDS.items():
        if keyword in model_name:
            return tier
    return "sonnet"  # default when no tier keywords match


class QualityEstimator:
    """
    Estimates task quality for a given (model, task_type) pair.

    Loads model metadata and task-type adjustments from models.yaml.
    Falls back to tier-based heuristics when config is unavailable.
    """

    def __init__(self, models_yaml: Optional[Path] = None) -> None:
        """
        Args:
            models_yaml: Optional path override for models.yaml.
                         Defaults to src/config/models.yaml relative to repo root.
        """
        self._yaml_path = models_yaml or self._find_models_yaml()
        self._models: Dict = {}
        self._adjustments: Dict = {}
        self._load_config()

    @property
    def config(self) -> Dict:
        """Return the loaded configuration as a dictionary."""
        return {
            "models": self._models,
            "task_type_adjustments": self._adjustments,
        }

    def _find_models_yaml(self) -> Optional[Path]:
        """Walk up directory tree to find src/config/models.yaml."""
        here = Path(__file__).parent
        for _ in range(4):
            candidate = here / "src" / "config" / "models.yaml"
            if candidate.exists():
                return candidate
            here = here.parent
        return None

    def _load_config(self) -> None:
        """Load model metadata and task adjustments from models.yaml."""
        if not self._yaml_path or not Path(self._yaml_path).exists():
            logger.warning("models.yaml not found at %s; using fallback quality heuristics", self._yaml_path)
            return
        try:
            with open(self._yaml_path) as fh:
                data = yaml.safe_load(fh) or {}
            # Support both top-level 'models' and nested 'model_selection.models'
            if "models" in data:
                self._models = data.get("models", {})
            else:
                sel = data.get("model_selection", {})
                self._models = sel.get("models", {})
            # Support both top-level 'task_type_adjustments' and nested structure
            if "task_type_adjustments" in data:
                self._adjustments = data.get("task_type_adjustments", {})
            else:
                sel = data.get("model_selection", {})
                self._adjustments = sel.get("task_quality_adjustments", {})
            logger.debug("Loaded quality config: %d models, %d task types", len(self._models), len(self._adjustments))
        except Exception as exc:
            logger.warning("Failed to load models.yaml quality config: %s", exc)

    def estimate_quality(self, model: str, task_type: str = "general") -> float:
        """
        Estimate task quality score for a (model, task_type) pair.

        Args:
            model:     Model name (e.g. 'claude-sonnet-4.6').
            task_type: Task type key (e.g. 'code_review', 'documentation').
                       Falls back to 'general' adjustments if unknown.

        Returns:
            Quality score in [0.0, 1.0].
        """
        meta = self._models.get(model)
        tier = _infer_tier(model)
        if meta:
            base_quality = float(meta.get("base_quality", _FALLBACK_TIER_QUALITY.get(tier, 0.75)))
            tier = meta.get("tier", tier)
        else:
            base_quality = _FALLBACK_TIER_QUALITY.get(tier, 0.75)
            logger.debug("Model '%s' not in config; using tier '%s' quality %.2f", model, tier, base_quality)

        task_adjustments = self._adjustments.get(task_type) or self._adjustments.get("general") or {}
        adj = task_adjustments.get(tier, 0.0)
        score = max(0.0, min(1.0, base_quality + adj))
        logger.debug("Quality for %s/%s: base=%.2f tier=%s adj=%.3f → %.3f", model, task_type, base_quality, tier, adj, score)
        return score

    def get_model_tier(self, model: str) -> str:
        """Return the quality tier for a model ('mini'|'haiku'|'sonnet'|'opus')."""
        meta = self._models.get(model)
        if meta:
            return meta.get("tier", _infer_tier(model))
        return _infer_tier(model)

    def get_avg_latency(self, model: str) -> float:
        """Return expected average latency in milliseconds for a model."""
        meta = self._models.get(model)
        if meta:
            # Support both average_latency_ms (preferred) and avg_latency_sec (fallback)
            if "average_latency_ms" in meta:
                return float(meta.get("average_latency_ms", 3000))
            elif "avg_latency_sec" in meta:
                return float(meta.get("avg_latency_sec", 3.0)) * 1000
        
        # Fallback to tier-based latency for unknown models
        tier = self.get_model_tier(model)
        return _FALLBACK_TIER_LATENCY.get(tier, 3000)  # default 3 seconds in ms

    def list_known_models(self) -> list:
        """Return list of all models defined in the config."""
        return list(self._models.keys())
