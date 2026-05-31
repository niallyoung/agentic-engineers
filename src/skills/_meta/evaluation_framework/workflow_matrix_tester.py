"""
Workflow Test Matrix Tester

Executes 5 workflows across 4 harnesses × 3 models (60 combinations).
Collects and aggregates metrics, detects anomalies, generates reports.
"""

import json
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import csv
from pathlib import Path

from .workflow_patterns import (
    WorkflowPattern,
    WORKFLOW_PATTERNS,
    HARNESSES,
    MODELS,
)


class AnomalyType(Enum):
    """Anomaly classification."""
    NONE = "none"
    HIGH_LATENCY = "high_latency"
    HIGH_COST = "high_cost"
    LOW_SUCCESS = "low_success"
    MULTIPLE = "multiple"


@dataclass
class WorkflowMetrics:
    """Metrics for a single workflow execution."""
    workflow: str
    harness: str
    model: str
    status: str  # "PASS", "FAIL", "ERROR", "TIMEOUT"
    total_latency_ms: int
    per_task_cost_usd: float
    success_rate: float  # 0.0 - 100.0
    token_count: int = 0
    error_count: int = 0
    escalation_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    workflow: str
    harness: str
    model: str
    anomaly_type: AnomalyType
    reasons: List[str] = field(default_factory=list)
    actual_values: Dict[str, float] = field(default_factory=dict)
    expected_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    def has_anomaly(self) -> bool:
        """Check if any anomaly detected."""
        return self.anomaly_type != AnomalyType.NONE


class WorkflowMetricsCollector:
    """Collects metrics across all workflow/harness/model combinations."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[WorkflowMetrics] = []
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.anomalies: List[AnomalyResult] = []
        self.execution_start = None
        self.execution_end = None
    
    def add_metric(self, metric: WorkflowMetrics):
        """Add a workflow execution metric."""
        self.metrics.append(metric)
    
    def calculate_baselines(self):
        """Calculate baseline metrics (median values)."""
        if not self.metrics:
            return
        
        for workflow in WORKFLOW_PATTERNS.keys():
            workflow_name = workflow.value
            workflow_metrics = [m for m in self.metrics if m.workflow == workflow_name]
            
            if not workflow_metrics:
                continue
            
            latencies = [m.total_latency_ms for m in workflow_metrics if m.status == "PASS"]
            costs = [m.per_task_cost_usd for m in workflow_metrics if m.status == "PASS"]
            success_rates = [m.success_rate for m in workflow_metrics if m.status == "PASS"]
            
            self.baselines[workflow_name] = {
                "median_latency_ms": statistics.median(latencies) if latencies else 0,
                "median_cost_usd": statistics.median(costs) if costs else 0.0,
                "median_success_rate": statistics.median(success_rates) if success_rates else 0.0,
            }
    
    def detect_anomalies(self):
        """Detect anomalies in metrics based on baselines."""
        if not self.baselines:
            self.calculate_baselines()
        
        for metric in self.metrics:
            baseline = self.baselines.get(metric.workflow, {})
            if not baseline:
                continue
            
            anomaly_type = AnomalyType.NONE
            reasons = []
            actual_values = {}
            expected_ranges = {}
            
            # Check latency anomaly
            median_latency = baseline.get("median_latency_ms", 0)
            if metric.status == "PASS" and median_latency > 0:
                if metric.total_latency_ms > median_latency * 2.0:
                    anomaly_type = AnomalyType.HIGH_LATENCY
                    reasons.append(
                        f"Latency {metric.total_latency_ms}ms > 2x median {median_latency}ms"
                    )
                    actual_values["latency_ms"] = metric.total_latency_ms
                    expected_ranges["latency_ms"] = (0, median_latency * 2.0)
            
            # Check cost anomaly
            median_cost = baseline.get("median_cost_usd", 0.0)
            if metric.status == "PASS" and median_cost > 0.0:
                if metric.per_task_cost_usd > median_cost * 2.0:
                    if anomaly_type == AnomalyType.HIGH_LATENCY:
                        anomaly_type = AnomalyType.MULTIPLE
                    else:
                        anomaly_type = AnomalyType.HIGH_COST
                    reasons.append(
                        f"Cost ${metric.per_task_cost_usd:.4f} > 2x median ${median_cost:.4f}"
                    )
                    actual_values["cost_usd"] = metric.per_task_cost_usd
                    expected_ranges["cost_usd"] = (0.0, median_cost * 2.0)
            
            # Check success rate anomaly
            if metric.success_rate < 95.0:
                if anomaly_type != AnomalyType.NONE:
                    anomaly_type = AnomalyType.MULTIPLE
                else:
                    anomaly_type = AnomalyType.LOW_SUCCESS
                reasons.append(f"Success rate {metric.success_rate:.1f}% < 95% threshold")
                actual_values["success_rate"] = metric.success_rate
                expected_ranges["success_rate"] = (95.0, 100.0)
            
            if anomaly_type != AnomalyType.NONE:
                self.anomalies.append(
                    AnomalyResult(
                        workflow=metric.workflow,
                        harness=metric.harness,
                        model=metric.model,
                        anomaly_type=anomaly_type,
                        reasons=reasons,
                        actual_values=actual_values,
                        expected_ranges=expected_ranges,
                    )
                )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics."""
        if not self.metrics:
            return {"error": "No metrics collected"}
        
        total = len(self.metrics)
        passed = sum(1 for m in self.metrics if m.status == "PASS")
        failed = sum(1 for m in self.metrics if m.status == "FAIL")
        errors = sum(1 for m in self.metrics if m.status == "ERROR")
        timeouts = sum(1 for m in self.metrics if m.status == "TIMEOUT")
        
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        total_cost = sum(m.per_task_cost_usd for m in self.metrics if m.status == "PASS")
        avg_latency = (
            statistics.mean([m.total_latency_ms for m in self.metrics if m.status == "PASS"])
            if any(m.status == "PASS" for m in self.metrics)
            else 0.0
        )
        
        by_workflow = {}
        for workflow in WORKFLOW_PATTERNS.keys():
            workflow_name = workflow.value
            workflow_metrics = [m for m in self.metrics if m.workflow == workflow_name]
            if workflow_metrics:
                workflow_passed = sum(1 for m in workflow_metrics if m.status == "PASS")
                by_workflow[workflow_name] = {
                    "total": len(workflow_metrics),
                    "passed": workflow_passed,
                    "pass_rate": (workflow_passed / len(workflow_metrics) * 100),
                }
        
        by_harness = {}
        for harness in HARNESSES:
            harness_metrics = [m for m in self.metrics if m.harness == harness]
            if harness_metrics:
                harness_passed = sum(1 for m in harness_metrics if m.status == "PASS")
                by_harness[harness] = {
                    "total": len(harness_metrics),
                    "passed": harness_passed,
                    "pass_rate": (harness_passed / len(harness_metrics) * 100),
                }
        
        by_model = {}
        for model in MODELS:
            model_metrics = [m for m in self.metrics if m.model == model]
            if model_metrics:
                model_passed = sum(1 for m in model_metrics if m.status == "PASS")
                by_model[model] = {
                    "total": len(model_metrics),
                    "passed": model_passed,
                    "pass_rate": (model_passed / len(model_metrics) * 100),
                }
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "timeouts": timeouts,
            "pass_rate": pass_rate,
            "total_cost_usd": total_cost,
            "avg_latency_ms": avg_latency,
            "execution_time_seconds": (
                (self.execution_end - self.execution_start)
                if self.execution_start and self.execution_end
                else None
            ),
            "by_workflow": by_workflow,
            "by_harness": by_harness,
            "by_model": by_model,
            "anomalies_detected": len(self.anomalies),
        }
    
    def export_json(self, filepath: Path) -> None:
        """Export metrics to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": self.get_summary(),
            "baselines": self.baselines,
            "metrics": [m.to_dict() for m in self.metrics],
            "anomalies": [
                {
                    "workflow": a.workflow,
                    "harness": a.harness,
                    "model": a.model,
                    "anomaly_type": a.anomaly_type.value,
                    "reasons": a.reasons,
                    "actual_values": a.actual_values,
                    "expected_ranges": a.expected_ranges,
                }
                for a in self.anomalies
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    
    def export_csv(self, filepath: Path) -> None:
        """Export metrics to CSV file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "workflow",
                    "harness",
                    "model",
                    "status",
                    "total_latency_ms",
                    "per_task_cost_usd",
                    "success_rate",
                    "token_count",
                    "error_count",
                    "escalation_count",
                    "timestamp",
                ],
            )
            writer.writeheader()
            for m in self.metrics:
                writer.writerow(m.to_dict())
    
    def export_markdown_matrix(self, filepath: Path) -> None:
        """Export colored success matrix to Markdown."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        lines = ["# Workflow Test Matrix\n"]
        lines.append(f"**Generated:** {datetime.utcnow().isoformat()}\n")
        lines.append(f"**Total Tests:** {len(self.metrics)}\n")
        lines.append(f"**Pass Rate:** {self.get_summary().get('pass_rate', 0.0):.1f}%\n\n")
        
        # Create matrix: workflows × (harness × model combinations)
        for workflow in WORKFLOW_PATTERNS.keys():
            workflow_name = workflow.value
            lines.append(f"## {workflow_name.upper()}\n\n")
            
            # Create sub-matrix for this workflow
            rows = []
            for harness in HARNESSES:
                row_data = []
                for model in MODELS:
                    metrics = [
                        m
                        for m in self.metrics
                        if m.workflow == workflow_name
                        and m.harness == harness
                        and m.model == model
                    ]
                    if metrics:
                        m = metrics[0]
                        anomaly_marker = ""
                        for a in self.anomalies:
                            if (
                                a.workflow == workflow_name
                                and a.harness == harness
                                and a.model == model
                            ):
                                anomaly_marker = " 🚨"
                                break
                        
                        status_icon = {
                            "PASS": "✅",
                            "FAIL": "❌",
                            "ERROR": "⚠️",
                            "TIMEOUT": "⏱️",
                        }.get(m.status, "❓")
                        
                        cell = (
                            f"{status_icon} {m.total_latency_ms}ms / "
                            f"${m.per_task_cost_usd:.4f}{anomaly_marker}"
                        )
                    else:
                        cell = "⚪ N/A"
                    row_data.append(cell)
                
                rows.append((harness, row_data))
            
            # Write table header
            lines.append("| Harness | Haiku | Sonnet | Opus |\n")
            lines.append("|---------|-------|--------|------|\n")
            
            # Write table rows
            for harness, row_data in rows:
                lines.append(f"| {harness} | " + " | ".join(row_data) + " |\n")
            
            lines.append("\n")
        
        # Add anomalies section
        if self.anomalies:
            lines.append("## Anomalies Detected\n\n")
            for a in self.anomalies:
                lines.append(f"**{a.workflow} / {a.harness} / {a.model}** 🚨\n")
                lines.append(f"- Type: {a.anomaly_type.value}\n")
                for reason in a.reasons:
                    lines.append(f"- {reason}\n")
                lines.append("\n")
        
        with open(filepath, "w") as f:
            f.writelines(lines)
