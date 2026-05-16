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
"""

from .metrics import MetricsRegistry, Counter, Gauge, Histogram
from .prometheus_exporter import PrometheusExporter
from .structured_logger import StructuredLogger, get_logger
from .tracing import Tracer, Span
from .health_check import HealthCheck, HealthStatus
from .slo_tracker import SLOTracker, SLO, SLOStatus
from .alerting import AlertManager, AlertRule, Alert, AlertSeverity

__all__ = [
    "MetricsRegistry", "Counter", "Gauge", "Histogram",
    "PrometheusExporter",
    "StructuredLogger", "get_logger",
    "Tracer", "Span",
    "HealthCheck", "HealthStatus",
    "SLOTracker", "SLO", "SLOStatus",
    "AlertManager", "AlertRule", "Alert", "AlertSeverity",
]
