"""
Regression Detection Engine for Continuous CI/CD Pipeline

Detects quality drops (>10%), latency increases (>25%), and new failures
by comparing current results against baseline snapshots.
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path


@dataclass
class RegressionMetrics:
    """Metrics for a test or suite."""
    test_id: str
    pass_rate: float  # 0.0-1.0
    avg_latency_ms: float
    failure_count: int
    error_count: int
    timestamp: str


@dataclass
class Regression:
    """Detected regression."""
    test_id: str
    regression_type: str  # "quality", "latency", "new_failure"
    severity: str  # "low", "medium", "high", "critical"
    baseline_value: float
    current_value: float
    change_percent: float
    description: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class RegressionDetector:
    """Detects regressions in evaluation results."""

    # Thresholds
    QUALITY_DROP_THRESHOLD = 0.10  # 10%
    LATENCY_INCREASE_THRESHOLD = 0.25  # 25%

    def __init__(self):
        """Initialize regression detector."""
        self.regressions: List[Regression] = []

    def detect(
        self,
        baseline: Dict[str, Any],
        current: Dict[str, Any]
    ) -> List[Regression]:
        """
        Detect regressions by comparing baseline and current results.

        Args:
            baseline: Baseline evaluation results
            current: Current evaluation results

        Returns:
            List of detected regressions
        """
        self.regressions = []

        # Get summaries
        baseline_summary = baseline.get("summary", {})
        current_summary = current.get("summary", {})

        # Detect quality drop
        baseline_pass_rate = baseline_summary.get("pass_rate", 100.0) / 100.0
        current_pass_rate = current_summary.get("pass_rate", 100.0) / 100.0
        quality_drop = baseline_pass_rate - current_pass_rate

        if quality_drop > self.QUALITY_DROP_THRESHOLD:
            severity = "critical" if quality_drop > 0.20 else "high"
            self.regressions.append(
                Regression(
                    test_id="overall_quality",
                    regression_type="quality",
                    severity=severity,
                    baseline_value=baseline_pass_rate * 100,
                    current_value=current_pass_rate * 100,
                    change_percent=-(quality_drop * 100),
                    description=f"Quality drop detected: {baseline_pass_rate*100:.1f}% → {current_pass_rate*100:.1f}%",
                )
            )

        # Detect latency increase
        baseline_latency = baseline_summary.get("avg_duration_ms", 0)
        current_latency = current_summary.get("avg_duration_ms", 0)

        if baseline_latency > 0:
            latency_increase = (current_latency - baseline_latency) / baseline_latency
            if latency_increase > self.LATENCY_INCREASE_THRESHOLD:
                severity = "high" if latency_increase > 0.50 else "medium"
                self.regressions.append(
                    Regression(
                        test_id="overall_latency",
                        regression_type="latency",
                        severity=severity,
                        baseline_value=baseline_latency,
                        current_value=current_latency,
                        change_percent=latency_increase * 100,
                        description=f"Latency increase detected: {baseline_latency:.0f}ms → {current_latency:.0f}ms",
                    )
                )

        # Detect new failures
        baseline_failed = set(baseline.get("failed_tests", []))
        current_failed = set(current.get("failed_tests", []))
        new_failures = current_failed - baseline_failed

        for failed_test in new_failures:
            self.regressions.append(
                Regression(
                    test_id=failed_test,
                    regression_type="new_failure",
                    severity="high",
                    baseline_value=0,
                    current_value=1,
                    change_percent=100.0,
                    description=f"New test failure: {failed_test}",
                )
            )

        # Detect regressions in by_harness
        if "by_harness" in baseline_summary and "by_harness" in current_summary:
            baseline_by_harness = baseline_summary["by_harness"]
            current_by_harness = current_summary["by_harness"]

            for harness, baseline_stats in baseline_by_harness.items():
                if harness not in current_by_harness:
                    continue

                current_stats = current_by_harness[harness]
                baseline_pass_rate = baseline_stats.get("pass_rate", 100.0) / 100.0
                current_pass_rate = current_stats.get("pass_rate", 100.0) / 100.0
                quality_drop = baseline_pass_rate - current_pass_rate

                if quality_drop > self.QUALITY_DROP_THRESHOLD:
                    severity = "high" if quality_drop > 0.15 else "medium"
                    self.regressions.append(
                        Regression(
                            test_id=f"harness_{harness}",
                            regression_type="quality",
                            severity=severity,
                            baseline_value=baseline_pass_rate * 100,
                            current_value=current_pass_rate * 100,
                            change_percent=-(quality_drop * 100),
                            description=f"Quality drop in {harness}: {baseline_pass_rate*100:.1f}% → {current_pass_rate*100:.1f}%",
                        )
                    )

        return self.regressions

    def get_critical_regressions(self) -> List[Regression]:
        """Get only critical and high severity regressions."""
        return [r for r in self.regressions if r.severity in ("critical", "high")]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of detected regressions."""
        return {
            "total_regressions": len(self.regressions),
            "critical": len([r for r in self.regressions if r.severity == "critical"]),
            "high": len([r for r in self.regressions if r.severity == "high"]),
            "medium": len([r for r in self.regressions if r.severity == "medium"]),
            "low": len([r for r in self.regressions if r.severity == "low"]),
            "quality_regressions": len(
                [r for r in self.regressions if r.regression_type == "quality"]
            ),
            "latency_regressions": len(
                [r for r in self.regressions if r.regression_type == "latency"]
            ),
            "failure_regressions": len(
                [r for r in self.regressions if r.regression_type == "new_failure"]
            ),
        }

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert regressions to list of dictionaries."""
        return [r.to_dict() for r in self.regressions]

    def to_markdown(self) -> str:
        """Generate markdown report of regressions."""
        if not self.regressions:
            return "## Regressions\n\nNo regressions detected.\n"

        summary = self.get_summary()
        markdown = f"""## Regressions Summary

- **Total:** {summary['total_regressions']}
- **Critical:** {summary['critical']}
- **High:** {summary['high']}
- **Medium:** {summary['medium']}
- **Low:** {summary['low']}

### By Type

- **Quality:** {summary['quality_regressions']}
- **Latency:** {summary['latency_regressions']}
- **New Failures:** {summary['failure_regressions']}

### Detailed Regressions

| Test ID | Type | Severity | Baseline | Current | Change | Description |
|---------|------|----------|----------|---------|--------|-------------|
"""
        for regression in sorted(self.regressions, key=lambda r: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}[r.severity],
            r.test_id
        )):
            markdown += f"| {regression.test_id} | {regression.regression_type} | {regression.severity} | {regression.baseline_value:.2f} | {regression.current_value:.2f} | {regression.change_percent:+.1f}% | {regression.description} |\n"

        return markdown
