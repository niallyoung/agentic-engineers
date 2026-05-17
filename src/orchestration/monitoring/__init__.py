"""
Monitoring & Observability for agentic-engineers Orchestrator.

Modules:
    metrics         — Counters, Gauges, Histograms collection
    prometheus      — Prometheus text-format exporter
    structured_logger — JSON structured logging
    tracing         — Distributed tracing (OpenTelemetry-style spans)
    health_check    — Health status endpoint
    slo_tracker     — SLO definition and tracking
    alerting        — Alert rule evaluation and firing
    token_tracker   — Token usage tracking and cost attribution
    budget_checker  — Budget enforcement and threshold checking
"""

from .metrics import MetricsRegistry, Counter, Gauge, Histogram
from .prometheus_exporter import PrometheusExporter
from .structured_logger import StructuredLogger, get_logger
from .tracing import Tracer, Span
from .health_check import HealthCheck, HealthStatus
from .slo_tracker import SLOTracker, SLO, SLOStatus
from .alerting import AlertManager, AlertRule, Alert, AlertSeverity
from .token_tracker import TokenTracker, TokenStats, TokenMetrics
from .budget_checker import BudgetChecker, BudgetStatus, BudgetResult

__all__ = [
    "MetricsRegistry", "Counter", "Gauge", "Histogram",
    "PrometheusExporter",
    "StructuredLogger", "get_logger",
    "Tracer", "Span",
    "HealthCheck", "HealthStatus",
    "SLOTracker", "SLO", "SLOStatus",
    "AlertManager", "AlertRule", "Alert", "AlertSeverity",
    "TokenTracker", "TokenStats", "TokenMetrics",
    "BudgetChecker", "BudgetStatus", "BudgetResult",
]
