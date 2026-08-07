# -*- coding: utf-8 -*-
"""
Model Selection Optimization Framework

Provides complexity-based routing, cost-quality tradeoff analysis,
A/B testing, and recommendations for optimal model selection.
"""

from .canonical_resolver import ModelResolver, ModelNotFoundError, ValidationError, FABLE_5_MODEL
from .complexity_scorer import ComplexityScorer, TaskAttributes, ComplexityLevel
from .model_selector import ModelSelector, ModelTier, RoutingDecision
from .cost_quality_analyzer import CostQualityAnalyzer, EfficiencyReport
from .ab_testing import ABTestingFramework, Experiment, ExperimentStatus
from .recommendations import RecommendationsEngine, Recommendation

__all__ = [
    "ModelResolver",
    "ModelNotFoundError",
    "ValidationError",
    "FABLE_5_MODEL",
    "ComplexityScorer",
    "TaskAttributes",
    "ComplexityLevel",
    "ModelSelector",
    "ModelTier",
    "RoutingDecision",
    "CostQualityAnalyzer",
    "EfficiencyReport",
    "ABTestingFramework",
    "Experiment",
    "ExperimentStatus",
    "RecommendationsEngine",
    "Recommendation",
]
