# -*- coding: utf-8 -*-
"""
CostAttributionMetrics — Integrate CostAttributor with MetricsRegistry.

Provides a bridge between CostAttributor (cost allocation logic) and
MetricsRegistry (metrics collection and reporting).

Usage:
    registry = MetricsRegistry()
    metrics = create_cost_metrics(registry)
    
    attribution_metrics = CostAttributionMetrics(registry, metrics)
    
    # After cost attribution
    result = attributor.attribute_cost(...)
    attribution_metrics.record_attribution(result)
"""

from __future__ import annotations

from typing import Dict, Optional
from src.orchestration.monitoring.metrics import MetricsRegistry, Gauge, Counter
from src.orchestration.models.cost_attributor import CostAttributionResult


class CostAttributionMetrics:
    """
    Record cost attribution results to MetricsRegistry.
    
    Thread-safe for concurrent updates.
    """
    
    def __init__(
        self,
        registry: MetricsRegistry,
        cost_metrics: Optional[Dict[str, object]] = None,
    ):
        """
        Initialize with MetricsRegistry and cost metrics dict.
        
        Args:
            registry: MetricsRegistry instance
            cost_metrics: Dict of cost metric objects (from create_cost_metrics)
        """
        self._registry = registry
        self._cost_metrics = cost_metrics or {}
    
    # ------------------------------------------------------------------
    # Recording API
    # ------------------------------------------------------------------
    
    def record_attribution(self, result: CostAttributionResult) -> None:
        """
        Record a cost attribution result to metrics.
        
        Updates:
          - cost_usd_by_role (counter with role label)
          - cost_usd_by_model (counter with model label)
          - cost_usd_by_task_type (counter with task_type label)
          - cost_usd_daily (gauge with date label)
          - cost_per_task_histogram (histogram)
        
        Args:
            result: CostAttributionResult from CostAttributor
        """
        # Record total cost
        self._record_total_cost(result.total_cost)
        
        # Record by dimension
        for agent, share in result.agent_shares.items():
            self._record_share(share, result.timestamp)
    
    def _record_total_cost(self, cost: float) -> None:
        """Record total cost to cost_per_task_histogram."""
        histogram = self._registry.histogram(
            "orchestrator_cost_per_task",
            "Distribution of cost per task in USD",
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
        )
        histogram.observe(cost)
    
    def _record_share(self, share, timestamp: str) -> None:
        """Record individual agent share to all relevant metrics."""
        # By role
        self._record_by_role(share.role, share.cost)
        
        # By model
        self._record_by_model(share.model, share.cost)
        
        # By task type
        if share.task_type:
            self._record_by_task_type(share.task_type, share.cost)
        
        # By date
        if timestamp:
            date = timestamp[:10]
            self._record_by_date(date, share.cost)
    
    def _record_by_role(self, role: str, cost: float) -> None:
        """Record cost by role."""
        counter = self._registry.counter(
            "orchestrator_cost_usd_by_role",
            "Total cost in USD by role",
            labels={"role": role},
        )
        counter.inc(cost)
    
    def _record_by_model(self, model: str, cost: float) -> None:
        """Record cost by model."""
        counter = self._registry.counter(
            "orchestrator_cost_usd_by_model",
            "Total cost in USD by model",
            labels={"model": model},
        )
        counter.inc(cost)
    
    def _record_by_task_type(self, task_type: str, cost: float) -> None:
        """Record cost by task type."""
        counter = self._registry.counter(
            "orchestrator_cost_usd_by_task_type",
            "Total cost in USD by task type",
            labels={"task_type": task_type},
        )
        counter.inc(cost)
    
    def _record_by_date(self, date: str, cost: float) -> None:
        """Record cost by date (daily aggregation)."""
        gauge = self._registry.gauge(
            "orchestrator_cost_usd_daily",
            "Daily cost in USD",
            labels={"date": date},
        )
        # For daily aggregation, we accumulate
        current = gauge.value
        gauge.set(current + cost)
    
    # ------------------------------------------------------------------
    # Reporting API
    # ------------------------------------------------------------------
    
    def get_cost_by_role(self) -> Dict[str, float]:
        """Get total cost by role from registry."""
        costs = {}
        all_metrics = self._registry.get_all()
        for key, metric in all_metrics.items():
            if "cost_usd_by_role" in key and hasattr(metric, 'value'):
                if hasattr(metric, 'labels') and 'role' in metric.labels:
                    role = metric.labels['role']
                    costs[role] = metric.value
        return costs
    
    def get_cost_by_model(self) -> Dict[str, float]:
        """Get total cost by model from registry."""
        costs = {}
        all_metrics = self._registry.get_all()
        for key, metric in all_metrics.items():
            if "cost_usd_by_model" in key and hasattr(metric, 'value'):
                if hasattr(metric, 'labels') and 'model' in metric.labels:
                    model = metric.labels['model']
                    costs[model] = metric.value
        return costs
    
    def get_cost_by_task_type(self) -> Dict[str, float]:
        """Get total cost by task type from registry."""
        costs = {}
        all_metrics = self._registry.get_all()
        for key, metric in all_metrics.items():
            if "cost_usd_by_task_type" in key and hasattr(metric, 'value'):
                if hasattr(metric, 'labels') and 'task_type' in metric.labels:
                    task_type = metric.labels['task_type']
                    costs[task_type] = metric.value
        return costs
    
    def get_cost_by_date(self) -> Dict[str, float]:
        """Get daily costs from registry."""
        costs = {}
        all_metrics = self._registry.get_all()
        for key, metric in all_metrics.items():
            if "cost_usd_daily" in key and hasattr(metric, 'value'):
                if hasattr(metric, 'labels') and 'date' in metric.labels:
                    date = metric.labels['date']
                    costs[date] = metric.value
        return costs
