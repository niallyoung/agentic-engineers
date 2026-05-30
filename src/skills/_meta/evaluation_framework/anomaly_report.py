"""
Anomaly Report Generator

Generates detailed anomaly analysis reports with:
- Anomaly classification and grouping
- Statistical analysis
- Regression detection
- Recommendation generation
"""

from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics

from .workflow_matrix_tester import WorkflowMetrics, AnomalyResult, AnomalyType


@dataclass
class AnomalyGroup:
    """Groups related anomalies."""
    anomaly_type: AnomalyType
    count: int
    affected_workflows: List[str] = field(default_factory=list)
    affected_harnesses: List[str] = field(default_factory=list)
    affected_models: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical
    impact_estimate: str = ""  # Brief description of impact


class AnomalyReportGenerator:
    """Generates anomaly reports from test results."""
    
    def __init__(self, metrics: List[WorkflowMetrics], anomalies: List[AnomalyResult]):
        """Initialize report generator."""
        self.metrics = metrics
        self.anomalies = anomalies
    
    def group_anomalies(self) -> Dict[AnomalyType, AnomalyGroup]:
        """Group anomalies by type."""
        groups = {}
        
        for anomaly_type in AnomalyType:
            matching = [a for a in self.anomalies if a.anomaly_type == anomaly_type]
            if not matching:
                continue
            
            group = AnomalyGroup(
                anomaly_type=anomaly_type,
                count=len(matching),
                affected_workflows=list(set(a.workflow for a in matching)),
                affected_harnesses=list(set(a.harness for a in matching)),
                affected_models=list(set(a.model for a in matching)),
            )
            
            # Determine severity
            if anomaly_type == AnomalyType.MULTIPLE:
                group.severity = "critical"
                group.impact_estimate = "Multiple anomalies on same execution"
            elif anomaly_type == AnomalyType.LOW_SUCCESS:
                group.severity = "critical"
                group.impact_estimate = "Success rate below 95% threshold - production risk"
            elif anomaly_type == AnomalyType.HIGH_COST:
                if group.count >= len(matching) * 0.5:
                    group.severity = "high"
                    group.impact_estimate = "50%+ of tests have cost spikes"
                else:
                    group.severity = "medium"
                    group.impact_estimate = "Isolated cost spikes detected"
            elif anomaly_type == AnomalyType.HIGH_LATENCY:
                if group.count >= len(matching) * 0.3:
                    group.severity = "high"
                    group.impact_estimate = "Widespread latency increase"
                else:
                    group.severity = "medium"
                    group.impact_estimate = "Isolated latency spikes"
            
            groups[anomaly_type] = group
        
        return groups
    
    def detect_regressions(self) -> List[Dict[str, Any]]:
        """Detect potential regressions."""
        regressions = []
        
        # Check for systematic failures by harness
        for harness in set(m.harness for m in self.metrics):
            harness_metrics = [m for m in self.metrics if m.harness == harness]
            harness_pass_rate = (
                sum(1 for m in harness_metrics if m.status == "PASS")
                / len(harness_metrics)
                * 100
            )
            
            if harness_pass_rate < 90.0:
                regressions.append({
                    "type": "HARNESS_FAILURE_RATE",
                    "harness": harness,
                    "pass_rate": harness_pass_rate,
                    "metric_count": len(harness_metrics),
                    "severity": "high" if harness_pass_rate < 80.0 else "medium",
                })
        
        # Check for systematic failures by model
        for model in set(m.model for m in self.metrics):
            model_metrics = [m for m in self.metrics if m.model == model]
            model_pass_rate = (
                sum(1 for m in model_metrics if m.status == "PASS")
                / len(model_metrics)
                * 100
            )
            
            if model_pass_rate < 90.0:
                regressions.append({
                    "type": "MODEL_FAILURE_RATE",
                    "model": model,
                    "pass_rate": model_pass_rate,
                    "metric_count": len(model_metrics),
                    "severity": "high" if model_pass_rate < 80.0 else "medium",
                })
        
        # Check for systematic failures by workflow
        from .workflow_patterns import WORKFLOW_PATTERNS
        for workflow in WORKFLOW_PATTERNS.keys():
            workflow_name = workflow.value
            workflow_metrics = [m for m in self.metrics if m.workflow == workflow_name]
            if not workflow_metrics:
                continue
            
            workflow_pass_rate = (
                sum(1 for m in workflow_metrics if m.status == "PASS")
                / len(workflow_metrics)
                * 100
            )
            
            expected_rate = WORKFLOW_PATTERNS[workflow].expected_success_rate
            
            if workflow_pass_rate < expected_rate - 5.0:
                regressions.append({
                    "type": "WORKFLOW_REGRESSION",
                    "workflow": workflow_name,
                    "expected_rate": expected_rate,
                    "actual_rate": workflow_pass_rate,
                    "metric_count": len(workflow_metrics),
                    "severity": "high" if workflow_pass_rate < expected_rate - 10.0 else "medium",
                })
        
        return regressions
    
    def generate_markdown_report(self) -> str:
        """Generate a comprehensive Markdown report."""
        lines = []
        
        lines.append("# Anomaly Analysis Report\n")
        lines.append(f"**Total Tests:** {len(self.metrics)}\n")
        lines.append(f"**Total Anomalies:** {len(self.anomalies)}\n")
        
        # Overall statistics
        passed = sum(1 for m in self.metrics if m.status == "PASS")
        pass_rate = (passed / len(self.metrics) * 100) if self.metrics else 0.0
        lines.append(f"**Pass Rate:** {pass_rate:.1f}%\n\n")
        
        # Anomaly groups
        groups = self.group_anomalies()
        if groups:
            lines.append("## Anomaly Groups\n\n")
            for anomaly_type, group in groups.items():
                lines.append(f"### {anomaly_type.value.upper()} (Severity: {group.severity})\n\n")
                lines.append(f"- **Count:** {group.count}\n")
                lines.append(f"- **Workflows:** {', '.join(group.affected_workflows)}\n")
                lines.append(f"- **Harnesses:** {', '.join(group.affected_harnesses)}\n")
                lines.append(f"- **Models:** {', '.join(group.affected_models)}\n")
                lines.append(f"- **Impact:** {group.impact_estimate}\n\n")
        
        # Regressions
        regressions = self.detect_regressions()
        if regressions:
            lines.append("## Regressions Detected\n\n")
            for regression in regressions:
                if regression["type"] == "HARNESS_FAILURE_RATE":
                    lines.append(
                        f"**{regression['harness']}** - Pass rate: {regression['pass_rate']:.1f}% "
                        f"({regression['metric_count']} tests)\n"
                    )
                elif regression["type"] == "MODEL_FAILURE_RATE":
                    lines.append(
                        f"**{regression['model']}** - Pass rate: {regression['pass_rate']:.1f}% "
                        f"({regression['metric_count']} tests)\n"
                    )
                elif regression["type"] == "WORKFLOW_REGRESSION":
                    lines.append(
                        f"**{regression['workflow']}** - Expected: {regression['expected_rate']:.1f}%, "
                        f"Actual: {regression['actual_rate']:.1f}% "
                        f"({regression['metric_count']} tests)\n"
                    )
            lines.append("\n")
        
        # Recommendations
        lines.append("## Recommendations\n\n")
        
        if groups.get(AnomalyType.LOW_SUCCESS):
            lines.append(
                "- **CRITICAL:** Address low success rate anomalies immediately. "
                "Success rate below 95% indicates production risk.\n"
            )
        
        if groups.get(AnomalyType.HIGH_LATENCY):
            lines.append(
                "- Investigate latency spikes. May indicate performance regression "
                "or resource contention.\n"
            )
        
        if groups.get(AnomalyType.HIGH_COST):
            lines.append(
                "- Review cost spikes. Consider model downgrade recommendations "
                "or workload optimization.\n"
            )
        
        if regressions:
            lines.append(
                "- Follow up on detected regressions. Run root cause analysis "
                "on affected harnesses/models/workflows.\n"
            )
        
        if not groups and not regressions:
            lines.append("- No critical anomalies detected. Framework performing as expected.\n")
        
        lines.append("\n")
        
        return "".join(lines)
    
    def generate_summary_table(self) -> str:
        """Generate a summary table of anomalies."""
        if not self.anomalies:
            return "No anomalies detected.\n"
        
        lines = []
        lines.append("| Workflow | Harness | Model | Type | Reasons |\n")
        lines.append("|----------|---------|-------|------|----------|\n")
        
        for anomaly in sorted(
            self.anomalies,
            key=lambda a: (a.workflow, a.harness, a.model)
        ):
            reason = anomaly.reasons[0] if anomaly.reasons else "Unknown"
            lines.append(
                f"| {anomaly.workflow} | {anomaly.harness} | {anomaly.model} | "
                f"{anomaly.anomaly_type.value} | {reason} |\n"
            )
        
        return "".join(lines)
