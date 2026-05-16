"""
Metrics Collection — Counters, Gauges, and Histograms.

Provides a thread-safe in-memory metrics registry for collecting
operational metrics from the Orchestrator and agents.

Usage:
    registry = MetricsRegistry()
    counter = registry.counter("tasks_total", labels={"role": "engineer"})
    counter.inc()

    gauge = registry.gauge("queue_depth")
    gauge.set(42)

    histogram = registry.histogram("task_duration_seconds", buckets=[1, 5, 10, 30, 60])
    histogram.observe(7.3)
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Metric types
# ---------------------------------------------------------------------------

class Counter:
    """Monotonically increasing counter."""

    def __init__(self, name: str, description: str = "", labels: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._value: float = 0.0
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0) -> None:
        """Increment counter by amount (must be >= 0)."""
        if amount < 0:
            raise ValueError(f"Counter increment must be non-negative, got {amount}")
        with self._lock:
            self._value += amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset counter to zero (for testing only)."""
        with self._lock:
            self._value = 0.0

    def __repr__(self) -> str:
        return f"Counter({self.name}={self._value}, labels={self.labels})"


class Gauge:
    """Gauge that can increase or decrease."""

    def __init__(self, name: str, description: str = "", labels: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._value: float = 0.0
        self._lock = threading.Lock()

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge."""
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def __repr__(self) -> str:
        return f"Gauge({self.name}={self._value}, labels={self.labels})"


class Histogram:
    """Histogram for tracking distributions (latency, size, etc.)."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Dict[str, str] = None,
        buckets: List[float] = None,
    ):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._lock = threading.Lock()
        self._count: int = 0
        self._sum: float = 0.0
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._bucket_counts[float("inf")] = 0

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._count += 1
            self._sum += value
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
            self._bucket_counts[float("inf")] += 1

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    @property
    def sum(self) -> float:
        with self._lock:
            return self._sum

    @property
    def bucket_counts(self) -> Dict[float, int]:
        with self._lock:
            return dict(self._bucket_counts)

    def percentile(self, p: float) -> Optional[float]:
        """Estimate percentile from bucket data (linear interpolation)."""
        if self._count == 0:
            return None
        target = self._count * (p / 100.0)
        prev_count = 0
        prev_bound = 0.0
        for bound in self.buckets:
            count = self._bucket_counts[bound]
            if count >= target:
                if count == prev_count:
                    return bound
                fraction = (target - prev_count) / (count - prev_count)
                return prev_bound + fraction * (bound - prev_bound)
            prev_count = count
            prev_bound = bound
        return self.buckets[-1]

    def __repr__(self) -> str:
        return f"Histogram({self.name}, count={self._count}, sum={self._sum})"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self._metrics: Dict[str, object] = {}
        self._lock = threading.Lock()

    def _key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def counter(self, name: str, description: str = "", labels: Dict[str, str] = None) -> Counter:
        """Get or create a Counter."""
        key = self._key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Counter(name, description, labels)
            return self._metrics[key]

    def gauge(self, name: str, description: str = "", labels: Dict[str, str] = None) -> Gauge:
        """Get or create a Gauge."""
        key = self._key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Gauge(name, description, labels)
            return self._metrics[key]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Dict[str, str] = None,
        buckets: List[float] = None,
    ) -> Histogram:
        """Get or create a Histogram."""
        key = self._key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Histogram(name, description, labels, buckets)
            return self._metrics[key]

    def get_all(self) -> Dict[str, object]:
        """Return snapshot of all registered metrics."""
        with self._lock:
            return dict(self._metrics)

    def clear(self) -> None:
        """Clear all metrics (for testing)."""
        with self._lock:
            self._metrics.clear()


# ---------------------------------------------------------------------------
# Pre-defined Orchestrator metrics
# ---------------------------------------------------------------------------

def create_orchestrator_metrics(registry: MetricsRegistry) -> Dict[str, object]:
    """
    Create and register the standard Orchestrator metrics.

    Returns a dict of named metric objects for easy access.
    """
    return {
        # Task lifecycle counters
        "tasks_total": registry.counter(
            "orchestrator_tasks_total",
            "Total number of tasks processed",
        ),
        "tasks_completed": registry.counter(
            "orchestrator_tasks_completed_total",
            "Total number of tasks completed successfully",
        ),
        "tasks_failed": registry.counter(
            "orchestrator_tasks_failed_total",
            "Total number of tasks that failed",
        ),
        "tasks_retried": registry.counter(
            "orchestrator_tasks_retried_total",
            "Total number of task retries",
        ),

        # Queue metrics
        "queue_depth": registry.gauge(
            "orchestrator_queue_depth",
            "Current number of tasks in queue",
        ),
        "queue_processing": registry.gauge(
            "orchestrator_queue_processing",
            "Current number of tasks being processed",
        ),

        # Latency histograms
        "task_duration_seconds": registry.histogram(
            "orchestrator_task_duration_seconds",
            "Task execution duration in seconds",
            buckets=[1, 5, 10, 30, 60, 120, 300, 600],
        ),
        "routing_latency_seconds": registry.histogram(
            "orchestrator_routing_latency_seconds",
            "Time to route a task to an agent",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        ),

        # Quality metrics
        "quality_score": registry.histogram(
            "orchestrator_quality_score",
            "Task quality scores from Quality Engineer",
            buckets=[10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95, 100],
        ),

        # Token usage (legacy, kept for compatibility)
        "tokens_total": registry.counter(
            "orchestrator_tokens_total",
            "Total tokens consumed across all tasks",
        ),
        
        # Token breakdown counters
        "tokens_input_total": registry.counter(
            "orchestrator_tokens_input_total",
            "Total input tokens consumed across all tasks",
        ),
        "tokens_output_total": registry.counter(
            "orchestrator_tokens_output_total",
            "Total output tokens consumed across all tasks",
        ),
        "tokens_cached_total": registry.counter(
            "orchestrator_tokens_cached_total",
            "Total cached tokens read across all tasks",
        ),
        
        # Cost tracking
        "cost_usd_total": registry.counter(
            "orchestrator_cost_usd_total",
            "Total cost in USD across all tasks",
        ),
        
        # Token distribution histograms
        "tokens_per_task": registry.histogram(
            "orchestrator_tokens_per_task",
            "Distribution of tokens consumed per task",
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000],
        ),
        "cost_per_task": registry.histogram(
            "orchestrator_cost_per_task",
            "Distribution of cost per task in USD",
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
        ),

        # Error counters
        "errors_total": registry.counter(
            "orchestrator_errors_total",
            "Total number of errors encountered",
        ),
        "validation_errors": registry.counter(
            "orchestrator_validation_errors_total",
            "Total DELEGATE/HANDBACK validation errors",
        ),
    }


# ---------------------------------------------------------------------------
# Token and Cost Metrics (with labels)
# ---------------------------------------------------------------------------

def create_token_metrics(registry: MetricsRegistry) -> Dict[str, object]:
    """
    Create token metrics with role and model labels.
    
    Returns a dict of metric objects for tracking token usage by role and model.
    """
    return {
        # Token counters by role
        "tokens_input_by_role": registry.counter(
            "orchestrator_tokens_input_by_role",
            "Input tokens consumed by role",
        ),
        "tokens_output_by_role": registry.counter(
            "orchestrator_tokens_output_by_role",
            "Output tokens consumed by role",
        ),
        "tokens_cached_by_role": registry.counter(
            "orchestrator_tokens_cached_by_role",
            "Cached tokens read by role",
        ),
        
        # Token counters by model
        "tokens_input_by_model": registry.counter(
            "orchestrator_tokens_input_by_model",
            "Input tokens consumed by model",
        ),
        "tokens_output_by_model": registry.counter(
            "orchestrator_tokens_output_by_model",
            "Output tokens consumed by model",
        ),
        
        # Token histograms
        "tokens_per_task_histogram": registry.histogram(
            "orchestrator_tokens_per_task",
            "Distribution of total tokens per task",
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000],
        ),
    }


def create_cost_metrics(registry: MetricsRegistry) -> Dict[str, object]:
    """
    Create cost metrics with role, model, and task type labels.
    
    Returns a dict of metric objects for tracking costs by various dimensions.
    """
    return {
        # Cost counters by role
        "cost_usd_by_role": registry.counter(
            "orchestrator_cost_usd_by_role",
            "Total cost in USD by role",
        ),
        
        # Cost counters by model
        "cost_usd_by_model": registry.counter(
            "orchestrator_cost_usd_by_model",
            "Total cost in USD by model",
        ),
        
        # Cost counters by task type
        "cost_usd_by_task_type": registry.counter(
            "orchestrator_cost_usd_by_task_type",
            "Total cost in USD by task type",
        ),
        
        # Cost gauge by date (daily aggregation)
        "cost_usd_daily": registry.gauge(
            "orchestrator_cost_usd_daily",
            "Daily cost in USD",
        ),
        
        # Cost histograms
        "cost_per_task_histogram": registry.histogram(
            "orchestrator_cost_per_task",
            "Distribution of cost per task in USD",
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
        ),
        
        # Cost efficiency metrics
        "cost_per_quality_point": registry.histogram(
            "orchestrator_cost_per_quality_point",
            "Cost per quality point achieved",
            buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
        ),
    }
