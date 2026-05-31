"""
Model Compatibility Matrix: Comprehensive framework for testing model compatibility
across scenarios with quality, latency, tokens, cost, and error rate metrics.

Features:
- 5 distinct test scenarios (simple, complex, code-fix, reasoning, security)
- Per-test metrics: latency (ms), quality (0-100), tokens, cost (USD), error rate (%)
- Regression detection: quality decline >10%, latency increase >25%
- Colored matrix visualization with emojis (✅ 🟡 ❌)
- CLI support: evals-model-matrix --model opus --scenario code-fix
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import json
from pathlib import Path
from datetime import datetime

from .framework import TestResult, TestStatus, CompatibilityMatrix


class TestScenario(Enum):
    """Test scenario types for model compatibility matrix."""
    SIMPLE = "simple"              # Basic task execution
    COMPLEX = "complex"            # Multi-step reasoning
    CODE_FIX = "code-fix"          # Bug fixing capability
    REASONING = "reasoning"        # Complex logical reasoning
    SECURITY = "security"          # Security-critical decisions


@dataclass
class ScenarioMetrics:
    """Metrics for a single test scenario execution."""
    scenario: TestScenario
    model: str
    harness: str
    latency_ms: int
    quality_score: float  # 0-100
    tokens_used: int
    cost_usd: float
    error_rate: float  # 0-100
    status: TestStatus = TestStatus.PASS
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario": self.scenario.value,
            "model": self.model,
            "harness": self.harness,
            "latency_ms": self.latency_ms,
            "quality_score": self.quality_score,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "error_rate": self.error_rate,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }


@dataclass
class ModelCompatibilityMatrix:
    """
    Model Compatibility Matrix: Tests all models (Haiku, Sonnet, Opus)
    across all scenarios with comprehensive metrics.
    """
    
    results: List[ScenarioMetrics] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Regression thresholds
    quality_regression_threshold: float = 10.0  # % quality drop
    latency_regression_threshold: float = 25.0  # % latency increase
    
    def add_result(self, metric: ScenarioMetrics):
        """Add a scenario metrics result."""
        self.results.append(metric)
    
    def get_summary_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Get summary statistics grouped by model."""
        by_model = {}
        
        # First pass: collect stats
        for result in self.results:
            if result.model not in by_model:
                by_model[result.model] = {
                    "count": 0,
                    "passed": 0,
                    "failed": 0,
                    "quality_sum": 0.0,
                    "latency_sum": 0.0,
                    "tokens_sum": 0.0,
                    "error_sum": 0.0,
                    "total_cost_usd": 0.0,
                    "scenarios": set(),
                }
            
            stats = by_model[result.model]
            stats["count"] += 1
            if result.status == TestStatus.PASS:
                stats["passed"] += 1
            else:
                stats["failed"] += 1
            stats["quality_sum"] += result.quality_score
            stats["latency_sum"] += result.latency_ms
            stats["tokens_sum"] += result.tokens_used
            stats["error_sum"] += result.error_rate
            stats["total_cost_usd"] += result.cost_usd
            stats["scenarios"].add(result.scenario.value)
        
        # Calculate averages and clean up
        for model in by_model:
            stats = by_model[model]
            count = stats["count"]
            if count > 0:
                stats["avg_quality"] = round(stats["quality_sum"] / count, 2)
                stats["avg_latency_ms"] = round(stats["latency_sum"] / count, 2)
                stats["avg_tokens"] = int(stats["tokens_sum"] / count)
                stats["avg_error_rate"] = round(stats["error_sum"] / count, 2)
                stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
            
            # Remove temporary keys
            stats.pop("quality_sum", None)
            stats.pop("latency_sum", None)
            stats.pop("tokens_sum", None)
            stats.pop("error_sum", None)
            stats["scenarios"] = sorted(list(stats["scenarios"]))
        
        return by_model
    
    def get_summary_by_scenario(self) -> Dict[str, Dict[str, Any]]:
        """Get summary statistics grouped by scenario."""
        by_scenario = {}
        
        # First pass: collect stats
        for result in self.results:
            scenario = result.scenario.value
            if scenario not in by_scenario:
                by_scenario[scenario] = {
                    "count": 0,
                    "passed": 0,
                    "failed": 0,
                    "quality_sum": 0.0,
                    "latency_sum": 0.0,
                    "tokens_sum": 0.0,
                    "total_cost_usd": 0.0,
                    "models": set(),
                }
            
            stats = by_scenario[scenario]
            stats["count"] += 1
            if result.status == TestStatus.PASS:
                stats["passed"] += 1
            else:
                stats["failed"] += 1
            stats["quality_sum"] += result.quality_score
            stats["latency_sum"] += result.latency_ms
            stats["tokens_sum"] += result.tokens_used
            stats["total_cost_usd"] += result.cost_usd
            stats["models"].add(result.model)
        
        # Calculate averages and clean up
        for scenario in by_scenario:
            stats = by_scenario[scenario]
            count = stats["count"]
            if count > 0:
                stats["avg_quality"] = round(stats["quality_sum"] / count, 2)
                stats["avg_latency_ms"] = round(stats["latency_sum"] / count, 2)
                stats["avg_tokens"] = int(stats["tokens_sum"] / count)
                stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
            
            # Remove temporary keys
            stats.pop("quality_sum", None)
            stats.pop("latency_sum", None)
            stats.pop("tokens_sum", None)
            stats["models"] = sorted(list(stats["models"]))
        
        return by_scenario
    
    def detect_quality_regressions(self, baseline: float = 92.0) -> List[Dict[str, Any]]:
        """
        Detect quality regressions (quality decline > threshold%).
        
        Args:
            baseline: Baseline quality score (default 92.0)
            
        Returns:
            List of regression findings
        """
        regressions = []
        by_model_scenario = {}
        
        # Group by model:scenario
        for result in self.results:
            key = f"{result.model}:{result.scenario.value}"
            if key not in by_model_scenario:
                by_model_scenario[key] = []
            by_model_scenario[key].append(result.quality_score)
        
        # Check for regressions
        for key, scores in by_model_scenario.items():
            avg_quality = sum(scores) / len(scores) if scores else 0
            quality_drop = baseline - avg_quality
            if quality_drop > self.quality_regression_threshold:
                model, scenario = key.split(":")
                regressions.append({
                    "model": model,
                    "scenario": scenario,
                    "baseline": baseline,
                    "achieved": round(avg_quality, 2),
                    "drop_percent": round(quality_drop, 2),
                    "status": "❌ FAIL",
                    "type": "quality",
                })
        
        return regressions
    
    def detect_latency_regressions(self, baseline: float = 500.0) -> List[Dict[str, Any]]:
        """
        Detect latency regressions (latency increase > threshold%).
        
        Args:
            baseline: Baseline latency in ms (default 500.0)
            
        Returns:
            List of regression findings
        """
        regressions = []
        by_model_scenario = {}
        
        # Group by model:scenario
        for result in self.results:
            key = f"{result.model}:{result.scenario.value}"
            if key not in by_model_scenario:
                by_model_scenario[key] = []
            by_model_scenario[key].append(result.latency_ms)
        
        # Check for regressions
        for key, latencies in by_model_scenario.items():
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            latency_increase_pct = ((avg_latency - baseline) / baseline * 100) if baseline > 0 else 0
            if latency_increase_pct > self.latency_regression_threshold:
                model, scenario = key.split(":")
                regressions.append({
                    "model": model,
                    "scenario": scenario,
                    "baseline_ms": baseline,
                    "achieved_ms": round(avg_latency, 2),
                    "increase_percent": round(latency_increase_pct, 2),
                    "status": "⚠️ CAUTION",
                    "type": "latency",
                })
        
        return regressions
    
    def generate_colored_matrix(self, scenario: Optional[TestScenario] = None) -> str:
        """
        Generate colored compatibility matrix with emoji indicators.
        
        Args:
            scenario: Filter to specific scenario (default: show all)
            
        Returns:
            Formatted matrix string
        """
        # Filter results if scenario specified
        results = self.results
        if scenario:
            results = [r for r in results if r.scenario == scenario]
        
        models = sorted(set(r.model for r in results))
        harnesses = sorted(set(r.harness for r in results))
        
        lines = []
        lines.append("\n🔹 Model Compatibility Matrix\n")
        
        if scenario:
            lines.append(f"📋 Scenario: {scenario.value}\n")
        
        # Header
        header = "Model/Harness".ljust(15)
        for model in models:
            header += f" | {model.upper()}"
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data rows
        for harness in harnesses:
            row = harness.ljust(15)
            for model in models:
                matching = [r for r in results if r.harness == harness and r.model == model]
                
                if not matching:
                    row += " | ⚪"
                    continue
                
                # Determine status
                passed = sum(1 for r in matching if r.status == TestStatus.PASS)
                total = len(matching)
                pass_rate = (passed / total * 100) if total > 0 else 0
                avg_quality = sum(r.quality_score for r in matching) / total if matching else 0
                
                # Color code: ✅ (pass), 🟡 (caution), ❌ (fail)
                if pass_rate >= 90 and avg_quality >= 90:
                    status = "✅"
                elif pass_rate >= 70 or avg_quality >= 80:
                    status = "🟡"
                else:
                    status = "❌"
                
                row += f" | {status}"
            
            lines.append(row)
        
        return "\n".join(lines) + "\n"
    
    def to_json(self) -> Dict[str, Any]:
        """Convert matrix to JSON-serializable dictionary."""
        return {
            "generated_at": self.generated_at,
            "total_results": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "summary_by_model": self.get_summary_by_model(),
            "summary_by_scenario": self.get_summary_by_scenario(),
            "quality_regressions": self.detect_quality_regressions(),
            "latency_regressions": self.detect_latency_regressions(),
        }
    
    def save_json(self, path: Path):
        """Save matrix to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_json(), f, indent=2)
    
    @classmethod
    def from_json(cls, path: Path) -> "ModelCompatibilityMatrix":
        """Load matrix from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        matrix = cls()
        for result_data in data.get("results", []):
            metric = ScenarioMetrics(
                scenario=TestScenario(result_data["scenario"]),
                model=result_data["model"],
                harness=result_data["harness"],
                latency_ms=result_data["latency_ms"],
                quality_score=result_data["quality_score"],
                tokens_used=result_data["tokens_used"],
                cost_usd=result_data["cost_usd"],
                error_rate=result_data["error_rate"],
                status=TestStatus(result_data["status"]),
                timestamp=result_data["timestamp"],
            )
            matrix.add_result(metric)
        
        return matrix
