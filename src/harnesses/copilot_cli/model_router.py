"""ModelRouter: Intelligent model selection based on task complexity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class ComplexityScore:
    """Result of complexity analysis for a task."""

    score: int  # 0-100
    effort_factor: float  # 1.0-2.0
    has_thinking_requirements: bool
    description_complexity: int  # 0-100
    reasons: list[str]


@dataclass
class RoutingDecision:
    """Result of model selection."""

    model_name: str
    complexity_score: int
    estimated_tokens: int
    estimated_cost: float
    explanation: str
    routing_rule: str


@dataclass
class CostAnalysis:
    """Cost estimates for different models on a task."""

    task_id: str
    task_description: str
    base_tokens: int

    haiku_tokens: int
    haiku_cost: float
    haiku_suitable: bool

    sonnet_tokens: int
    sonnet_cost: float
    sonnet_suitable: bool

    opus_tokens: int
    opus_cost: float
    opus_suitable: bool

    recommended_model: str
    savings_with_haiku: Optional[float]  # vs recommended, if haiku suitable


class ModelRouter:
    """Intelligent model selection for Copilot harness based on task complexity."""

    # Model selection thresholds
    HAIKU_THRESHOLD = 30  # 0-30: Haiku
    SONNET_THRESHOLD = 70  # 31-70: Sonnet
    # 71-100: Opus

    # Token multipliers per complexity range
    BASE_TOKENS_LOW = 2000
    BASE_TOKENS_MEDIUM = 5000
    BASE_TOKENS_HIGH = 10000

    # Model pricing (USD per 1K tokens) - from models.yaml
    PRICING = {
        "claude-haiku-4.5": {
            "provider": "anthropic",
            "input": 0.00008,
            "output": 0.00024,
        },
        "claude-sonnet-4.5": {
            "provider": "anthropic",
            "input": 0.003,
            "output": 0.015,
        },
        "claude-sonnet-4.6": {
            "provider": "anthropic",
            "input": 0.003,
            "output": 0.015,
        },
        "claude-opus-4.8": {
            "provider": "anthropic",
            "input": 0.015,
            "output": 0.075,
        },
        "gpt-4o-mini": {
            "provider": "openai",
            "input": 0.00015,
            "output": 0.0006,
        },
        "gpt-4o": {
            "provider": "openai",
            "input": 0.0025,
            "output": 0.01,
        },
        "gpt-4-turbo": {
            "provider": "openai",
            "input": 0.01,
            "output": 0.03,
        },
        "gpt-4": {
            "provider": "openai",
            "input": 0.01,
            "output": 0.03,
        },
    }

    def __init__(self, models_yaml_path: Optional[Path] | str | None = None) -> None:
        """Initialize router with optional model config path."""
        if models_yaml_path is None:
            models_yaml_path = (
                Path(__file__).parent.parent / "config" / "models.yaml"
            )
        self.models_yaml_path = Path(models_yaml_path)

    def analyze_complexity(self, task_definition: Dict[str, Any]) -> ComplexityScore:
        """
        Analyze task complexity from definition.

        Args:
            task_definition: Dict with 'effort', 'description', 'thinking_required' fields

        Returns:
            ComplexityScore with 0-100 score and reasoning
        """
        score = 0
        reasons: List[str] = []
        effort_factor = 1.0
        has_thinking = False

        # 1. Parse effort field (0-40 points)
        effort = task_definition.get("effort", "").lower()
        effort_scores = {
            "low": (15, "low effort"),
            "medium": (30, "medium effort"),
            "high": (35, "high effort"),
            "max": (40, "max effort"),
        }

        effort_value, effort_desc = effort_scores.get(effort, (5, "unspecified effort"))
        score += effort_value
        reasons.append(f"Effort field: {effort_desc} (+{effort_value})")

        if effort == "max":
            effort_factor = 2.0

        # 2. Analyze description length and complexity (0-40 points)
        description = task_definition.get("description", "")
        if isinstance(description, str):
            desc_length = len(description)
            word_count = len(description.split())

            # Length score
            if desc_length < 100:
                desc_score = 5
                reasons.append("Description: very short (+5)")
            elif desc_length < 300:
                desc_score = 15
                reasons.append("Description: short (+15)")
            elif desc_length < 800:
                desc_score = 25
                reasons.append("Description: medium (+25)")
            else:
                desc_score = 35
                reasons.append("Description: long, complex (+35)")

            score += desc_score

            # Complexity indicators
            complexity_words = [
                "refactor",
                "architecture",
                "design",
                "multi-service",
                "integration",
                "migration",
                "performance",
                "scalability",
                "security",
                "async",
                "concurrent",
                "distributed",
                "cross-repo",
                "complex",
                "hard",
                "intricate",
            ]

            complexity_count = sum(
                1
                for word in complexity_words
                if word.lower() in description.lower()
            )

            if complexity_count >= 1:
                complexity_boost = min(15, complexity_count * 5)
                score += complexity_boost
                reasons.append(
                    f"High-complexity keywords detected (+{complexity_boost})"
                )

        # 3. Detect thinking requirements (0-20 points)
        thinking_fields = [
            task_definition.get("thinking_required"),
            task_definition.get("requires_thinking"),
            task_definition.get("thinking"),
        ]

        if any(thinking_fields):
            score += 20
            reasons.append("Thinking capability required (+20)")
            has_thinking = True

        # Check for thinking keywords in description
        thinking_keywords = [
            "analyze",
            "planning",
            "design",
            "architecture",
            "debug",
            "root cause",
            "understand",
            "investigate",
        ]
        if description and any(
            kw.lower() in description.lower() for kw in thinking_keywords
        ):
            score += 10
            reasons.append("Thinking indicators in description (+10)")
            has_thinking = True

        # 4. Check for special requirements (0-10 points)
        requirements = task_definition.get("requirements", [])
        if isinstance(requirements, list):
            if len(requirements) > 5:
                score += 5
                reasons.append("Many requirements (+5)")

        constraints = task_definition.get("constraints", [])
        if isinstance(constraints, list) and len(constraints) > 0:
            constraint_text = " ".join(constraints).lower()
            if any(
                word in constraint_text
                for word in ["backward compatibility", "performance", "security"]
            ):
                score += 5
                reasons.append("Strict constraints (+5)")

        # 5. Cap score at 100
        score = min(max(score, 0), 100)

        # Calculate description complexity metric
        desc_complexity = min(
            100, max(0, len(description) // 10) + (complexity_count * 10)
        )

        return ComplexityScore(
            score=score,
            effort_factor=effort_factor,
            has_thinking_requirements=has_thinking,
            description_complexity=desc_complexity,
            reasons=reasons,
        )

    def select_model(self, complexity_score: int) -> Tuple[str, str]:
        """
        Select appropriate model based on complexity score.

        Returns:
            Tuple of (model_name, routing_rule)
        """
        if complexity_score <= self.HAIKU_THRESHOLD:
            return "claude-haiku-4.5", "Complexity 0-30: Fast execution, cost-effective"
        elif complexity_score <= self.SONNET_THRESHOLD:
            return "claude-sonnet-4.6", "Complexity 31-70: Balanced capability and cost"
        else:
            return "claude-opus-4.8", "Complexity 71-100: Maximum capability for hard problems"

    def estimate_tokens(
        self,
        complexity_score: int,
        description: str = "",
        requirements: Optional[List[str]] = None,
    ) -> int:
        """
        Estimate token count for a task.

        Args:
            complexity_score: 0-100 from analyze_complexity
            description: Task description
            requirements: List of requirements

        Returns:
            Estimated token count
        """
        # Base tokens by complexity range
        if complexity_score <= self.HAIKU_THRESHOLD:
            base = self.BASE_TOKENS_LOW
        elif complexity_score <= self.SONNET_THRESHOLD:
            base = self.BASE_TOKENS_MEDIUM
        else:
            base = self.BASE_TOKENS_HIGH

        # Adjust by complexity ratio
        complexity_multiplier = 0.8 + (complexity_score / 100.0) * 1.2

        # Add for description size
        description_tokens = len(description.split()) // 4 if description else 0

        # Add for requirements
        requirements_tokens = (len(requirements) * 50) if requirements else 0

        total = int(base * complexity_multiplier + description_tokens + requirements_tokens)

        return total

    def estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate cost for a model running a task.

        Args:
            model: Model name
            tokens: Token count

        Returns:
            Estimated cost in USD
        """
        if model not in self.PRICING:
            return 0.0

        pricing = self.PRICING[model]

        # Assume 60% input, 40% output token ratio
        input_tokens = tokens * 0.6
        output_tokens = tokens * 0.4

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def route(self, task_definition: Dict[str, Any]) -> RoutingDecision:
        """
        Perform full routing decision for a task.

        Args:
            task_definition: Complete task definition dict

        Returns:
            RoutingDecision with model selection and reasoning
        """
        # Analyze complexity
        complexity = self.analyze_complexity(task_definition)

        # Select model
        model, routing_rule = self.select_model(complexity.score)

        # Estimate tokens
        description = task_definition.get("description", "")
        requirements = task_definition.get("requirements", [])
        tokens = self.estimate_tokens(complexity.score, description, requirements)

        # Estimate cost
        cost = self.estimate_cost(model, tokens)

        # Build explanation
        explanation = (
            f"Task complexity analyzed at {complexity.score}/100. "
            f"{len(complexity.reasons)} factors considered: "
            f"{'; '.join(complexity.reasons[:3])}. "
            f"Selected {model} model. "
            f"Estimated: {tokens:,} tokens (~${cost:.3f})."
        )

        return RoutingDecision(
            model_name=model,
            complexity_score=complexity.score,
            estimated_tokens=tokens,
            estimated_cost=cost,
            explanation=explanation,
            routing_rule=routing_rule,
        )

    def compare_models(self, task_definition: Dict[str, Any]) -> CostAnalysis:
        """
        Analyze costs across all three model tiers.

        Args:
            task_definition: Complete task definition dict

        Returns:
            CostAnalysis with comparison matrix
        """
        complexity = self.analyze_complexity(task_definition)
        description = task_definition.get("description", "")
        requirements = task_definition.get("requirements", [])

        # Get recommended model
        recommended_model, _ = self.select_model(complexity.score)

        # Estimate tokens for each model
        # Note: token count varies slightly by model capability
        haiku_tokens = self.estimate_tokens(complexity.score, description, requirements)
        sonnet_tokens = int(haiku_tokens * 0.95)  # Sonnet more efficient
        opus_tokens = int(haiku_tokens * 0.90)  # Opus most efficient

        # Calculate costs
        haiku_cost = self.estimate_cost("claude-haiku-4.5", haiku_tokens)
        sonnet_cost = self.estimate_cost("claude-sonnet-4.6", sonnet_tokens)
        opus_cost = self.estimate_cost("claude-opus-4.8", opus_tokens)

        # Determine suitability
        haiku_suitable = complexity.score <= self.HAIKU_THRESHOLD
        sonnet_suitable = (
            complexity.score <= self.SONNET_THRESHOLD or complexity.score < 80
        )
        opus_suitable = True  # Always suitable

        # Calculate potential savings
        recommended_cost = {
            "claude-haiku-4.5": haiku_cost,
            "claude-sonnet-4.6": sonnet_cost,
            "claude-opus-4.8": opus_cost,
        }[recommended_model]

        savings_with_haiku = None
        if haiku_suitable and recommended_model != "claude-haiku-4.5":
            savings_with_haiku = recommended_cost - haiku_cost

        return CostAnalysis(
            task_id=task_definition.get("task_id", "UNKNOWN"),
            task_description=description[:100],
            base_tokens=self.BASE_TOKENS_MEDIUM,
            haiku_tokens=haiku_tokens,
            haiku_cost=haiku_cost,
            haiku_suitable=haiku_suitable,
            sonnet_tokens=sonnet_tokens,
            sonnet_cost=sonnet_cost,
            sonnet_suitable=sonnet_suitable,
            opus_tokens=opus_tokens,
            opus_cost=opus_cost,
            opus_suitable=opus_suitable,
            recommended_model=recommended_model,
            savings_with_haiku=savings_with_haiku,
        )

    def get_cost_comparison_matrix(
        self, analyses: List[CostAnalysis]
    ) -> Dict[str, Any]:
        """
        Generate cost comparison matrix from multiple analyses.

        Args:
            analyses: List of CostAnalysis results

        Returns:
            Matrix with aggregated costs and savings
        """
        total_haiku = sum(a.haiku_cost for a in analyses)
        total_sonnet = sum(a.sonnet_cost for a in analyses)
        total_opus = sum(a.opus_cost for a in analyses)
        total_recommended = sum(
            {
                "claude-haiku-4.5": a.haiku_cost,
                "claude-sonnet-4.6": a.sonnet_cost,
                "claude-opus-4.8": a.opus_cost,
            }[a.recommended_model]
            for a in analyses
        )

        return {
            "total_tasks": len(analyses),
            "haiku_total_cost": round(total_haiku, 4),
            "sonnet_total_cost": round(total_sonnet, 4),
            "opus_total_cost": round(total_opus, 4),
            "recommended_total_cost": round(total_recommended, 4),
            "potential_savings_vs_sonnet": round(total_sonnet - total_haiku, 4),
            "potential_savings_vs_opus": round(total_opus - total_haiku, 4),
            "avg_complexity_score": round(
                sum(
                    a.haiku_tokens / 50 for a in analyses  # Rough mapping
                )
                / len(analyses),
                1,
            ),
        }


class CostAnalyzer:
    """Cost analysis module for model selection."""

    def __init__(self, router: ModelRouter | None = None) -> None:
        """Initialize cost analyzer."""
        self.router = router or ModelRouter()

    def analyze_batch(
        self, task_definitions: List[Dict[str, Any]]
    ) -> Tuple[List[CostAnalysis], Dict[str, Any]]:
        """
        Analyze costs for a batch of tasks.

        Args:
            task_definitions: List of task definition dicts

        Returns:
            Tuple of (list of CostAnalysis, comparison matrix)
        """
        analyses = [self.router.compare_models(task) for task in task_definitions]
        matrix = self.router.get_cost_comparison_matrix(analyses)

        return analyses, matrix

    def generate_cost_report(
        self, analyses: List[CostAnalysis]
    ) -> str:
        """
        Generate formatted cost report.

        Args:
            analyses: List of CostAnalysis results

        Returns:
            Formatted report string
        """
        lines = ["# Cost Analysis Report", ""]
        lines.append(f"Total tasks analyzed: {len(analyses)}")
        lines.append("")

        lines.append("| Task ID | Description | Haiku | Sonnet | Opus | Recommended |")
        lines.append("|---------|-------------|-------|--------|------|-------------|")

        total_haiku = 0.0
        total_sonnet = 0.0
        total_opus = 0.0

        for analysis in analyses:
            task_id = analysis.task_id
            desc = analysis.task_description[:40].replace("|", "-")
            haiku_str = f"${analysis.haiku_cost:.4f}"
            sonnet_str = f"${analysis.sonnet_cost:.4f}"
            opus_str = f"${analysis.opus_cost:.4f}"
            recommended = analysis.recommended_model.replace("claude-", "").upper()

            lines.append(
                f"| {task_id} | {desc} | {haiku_str} | {sonnet_str} | {opus_str} | {recommended} |"
            )

            total_haiku += analysis.haiku_cost
            total_sonnet += analysis.sonnet_cost
            total_opus += analysis.opus_cost

        lines.append("")
        lines.append("## Summary")
        lines.append(f"- Total with Haiku: ${total_haiku:.4f}")
        lines.append(f"- Total with Sonnet: ${total_sonnet:.4f}")
        lines.append(f"- Total with Opus: ${total_opus:.4f}")
        lines.append(
            f"- Potential savings (Haiku vs Sonnet): ${total_sonnet - total_haiku:.4f}"
        )

        return "\n".join(lines)
