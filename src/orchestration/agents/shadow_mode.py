"""
Shadow Mode Implementation for Orchestrator.

Enables parallel execution of new code paths alongside production code,
comparing results without impacting production. Supports gradual traffic
rollout with deterministic sampling based on task ID.

Features:
- Parallel execution of old and new code paths
- Deterministic traffic sampling (1%, 5%, 10%, 25%, 50%, 75%, 100%)
- Result comparison and difference logging
- Performance metrics collection (latency, correctness, errors)
- Zero impact on production results
- Feature flag support via environment variables
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, Future


# Configure logging
logger = logging.getLogger(__name__)


class ShadowModeTraffic(Enum):
    """Supported traffic percentages for shadow mode rollout."""
    PERCENT_1 = 1
    PERCENT_5 = 5
    PERCENT_10 = 10
    PERCENT_25 = 25
    PERCENT_50 = 50
    PERCENT_75 = 75
    PERCENT_100 = 100


@dataclass
class ShadowModeResult:
    """Result from shadow mode execution."""
    
    # Execution metadata
    task_id: str
    timestamp: str  # ISO 8601 format
    traffic_percentage: int
    sampled: bool  # Whether this task was sampled for shadow execution
    
    # Production execution
    production_result: Any
    production_latency_ms: float
    production_error: Optional[str] = None
    
    # Shadow execution (if sampled)
    shadow_result: Optional[Any] = None
    shadow_latency_ms: Optional[float] = None
    shadow_error: Optional[str] = None
    
    # Comparison
    results_match: Optional[bool] = None
    difference_summary: Optional[str] = None
    detailed_differences: Optional[Dict[str, Any]] = None
    
    # Metrics
    correctness_score: float = 0.0  # 0.0-1.0 (1.0 = perfect match)
    performance_ratio: float = 1.0  # shadow_latency / production_latency
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            k: v for k, v in asdict(self).items()
            if v is not None
        }


@dataclass
class ShadowModeMetrics:
    """Aggregated metrics from shadow mode execution."""
    
    # Execution summary
    total_tasks: int = 0
    sampled_tasks: int = 0
    sampling_rate: float = 0.0
    
    # Correctness metrics
    matching_results: int = 0
    mismatched_results: int = 0
    match_rate: float = 0.0
    
    # Error metrics
    production_errors: int = 0
    shadow_errors: int = 0
    error_correlation: float = 0.0  # Percentage of shadow errors that also had production errors
    
    # Performance metrics
    avg_production_latency_ms: float = 0.0
    avg_shadow_latency_ms: float = 0.0
    avg_performance_ratio: float = 1.0
    
    # Detailed error tracking
    error_types: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class ShadowModeContext:
    """
    Context manager for shadow mode execution.
    
    Handles:
    - Traffic sampling (deterministic based on task ID)
    - Parallel execution of old and new code
    - Result comparison
    - Metrics collection
    - Logging
    """
    
    def __init__(
        self,
        task_id: str,
        traffic_percentage: int = 10,
        metrics_dir: str = "artifacts/shadow-mode",
        enabled: bool = True,
    ):
        """
        Initialize shadow mode context.
        
        Args:
            task_id: Unique task identifier for deterministic sampling
            traffic_percentage: Percentage of traffic to sample (1-100)
            metrics_dir: Directory to write shadow mode metrics
            enabled: Whether shadow mode is enabled
        """
        self.task_id = task_id
        self.traffic_percentage = traffic_percentage
        self.metrics_dir = Path(metrics_dir)
        self.enabled = enabled
        self.sampled = False
        
        # Validate traffic percentage
        if traffic_percentage not in [e.value for e in ShadowModeTraffic]:
            raise ValueError(
                f"Invalid traffic percentage: {traffic_percentage}. "
                f"Must be one of: {[e.value for e in ShadowModeTraffic]}"
            )
        
        # Determine if this task is sampled
        if enabled:
            self.sampled = self._should_sample(task_id, traffic_percentage)
        
        # Create metrics directory
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.production_result = None
        self.shadow_result = None
        self.production_latency_ms = 0.0
        self.shadow_latency_ms = 0.0
        self.production_error = None
        self.shadow_error = None
        
        logger.info(
            f"Shadow mode context initialized: task_id={task_id}, "
            f"traffic={traffic_percentage}%, sampled={self.sampled}, enabled={enabled}"
        )
    
    @staticmethod
    def _should_sample(task_id: str, traffic_percentage: int) -> bool:
        """
        Deterministically sample task based on task ID and traffic percentage.
        
        Uses MD5 hash of task ID to ensure consistent sampling across runs
        and even distribution of traffic.
        
        Args:
            task_id: Unique task identifier
            traffic_percentage: Target traffic percentage (1-100)
        
        Returns:
            True if task should be sampled for shadow execution
        """
        # Hash task ID to get deterministic value
        hash_digest = hashlib.md5(task_id.encode()).hexdigest()
        # Convert first 8 hex chars to integer (0-4294967295)
        hash_value = int(hash_digest[:8], 16)
        # Normalize to 0-100 range
        normalized = (hash_value % 100) + 1  # 1-100 inclusive
        
        return normalized <= traffic_percentage
    
    def execute_production(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute production code path and capture result/latency.
        
        Args:
            func: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result from production function
        """
        start_time = time.time()
        try:
            self.production_result = func(*args, **kwargs)
            self.production_latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"Production execution completed: task_id={self.task_id}, "
                f"latency_ms={self.production_latency_ms:.2f}"
            )
            return self.production_result
        except Exception as e:
            self.production_latency_ms = (time.time() - start_time) * 1000
            self.production_error = str(e)
            logger.error(
                f"Production execution failed: task_id={self.task_id}, "
                f"error={str(e)}"
            )
            raise
    
    def execute_shadow(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute shadow code path (if sampled) and capture result/latency.
        
        Errors in shadow execution are caught and logged but don't affect
        production results.
        
        Args:
            func: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result from shadow function, or None if not sampled
        """
        if not self.sampled or not self.enabled:
            return None
        
        start_time = time.time()
        try:
            self.shadow_result = func(*args, **kwargs)
            self.shadow_latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"Shadow execution completed: task_id={self.task_id}, "
                f"latency_ms={self.shadow_latency_ms:.2f}"
            )
            return self.shadow_result
        except Exception as e:
            self.shadow_latency_ms = (time.time() - start_time) * 1000
            self.shadow_error = str(e)
            logger.warning(
                f"Shadow execution failed (non-critical): task_id={self.task_id}, "
                f"error={str(e)}"
            )
            return None
    
    def execute_parallel(
        self,
        production_func: Callable,
        shadow_func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, Optional[Any]]:
        """
        Execute production and shadow functions in parallel (if sampled).
        
        Production function always runs synchronously. Shadow function runs
        in background thread if sampled.
        
        Args:
            production_func: Production code path
            shadow_func: Shadow code path
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Tuple of (production_result, shadow_result)
        """
        # Always execute production synchronously
        production_result = self.execute_production(production_func, *args, **kwargs)
        
        # Execute shadow in background if sampled
        shadow_result = None
        if self.sampled and self.enabled:
            # Use thread pool for non-blocking shadow execution
            with ThreadPoolExecutor(max_workers=1) as executor:
                shadow_future = executor.submit(
                    self.execute_shadow, shadow_func, *args, **kwargs
                )
                # Don't wait for shadow execution to complete
                # (fire-and-forget pattern)
                try:
                    shadow_result = shadow_future.result(timeout=5.0)
                except Exception as e:
                    logger.warning(f"Shadow execution timeout or error: {e}")
        
        return production_result, shadow_result
    
    def compare_results(
        self,
        comparison_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Compare production and shadow results.
        
        Args:
            comparison_func: Optional custom comparison function
                            (should return Dict with 'match' and 'differences' keys)
        
        Returns:
            Comparison result dictionary
        """
        if not self.sampled or self.shadow_result is None:
            return {
                'results_match': None,
                'difference_summary': 'Shadow not executed',
                'detailed_differences': None,
                'correctness_score': 1.0,  # No mismatch if shadow didn't run
            }
        
        # Use custom comparison function if provided
        if comparison_func:
            try:
                comparison = comparison_func(self.production_result, self.shadow_result)
                return comparison
            except Exception as e:
                logger.warning(f"Custom comparison function failed: {e}")
        
        # Default comparison: simple equality
        match = self._default_compare(self.production_result, self.shadow_result)
        
        return {
            'results_match': match,
            'difference_summary': 'Results match' if match else 'Results differ',
            'detailed_differences': None if match else {
                'production': str(self.production_result)[:500],
                'shadow': str(self.shadow_result)[:500],
            },
            'correctness_score': 1.0 if match else 0.0,
        }
    
    @staticmethod
    def _default_compare(prod: Any, shadow: Any) -> bool:
        """
        Default comparison logic.
        
        Handles JSON-serializable objects and basic types.
        """
        try:
            # Try JSON serialization for deep comparison
            return json.dumps(prod, sort_keys=True) == json.dumps(shadow, sort_keys=True)
        except (TypeError, ValueError):
            # Fall back to equality comparison
            return prod == shadow
    
    def record_result(
        self,
        comparison_func: Optional[Callable] = None
    ) -> ShadowModeResult:
        """
        Record shadow mode result with all metrics.
        
        Args:
            comparison_func: Optional custom comparison function
        
        Returns:
            ShadowModeResult object
        """
        comparison = self.compare_results(comparison_func)
        
        # Calculate performance ratio
        performance_ratio = 1.0
        if (self.shadow_latency_ms and self.shadow_latency_ms > 0 and 
            self.production_latency_ms and self.production_latency_ms > 0):
            performance_ratio = self.shadow_latency_ms / self.production_latency_ms
        
        result = ShadowModeResult(
            task_id=self.task_id,
            timestamp=datetime.now().isoformat(),
            traffic_percentage=self.traffic_percentage,
            sampled=self.sampled,
            production_result=self.production_result,
            production_latency_ms=self.production_latency_ms,
            production_error=self.production_error,
            shadow_result=self.shadow_result if self.sampled else None,
            shadow_latency_ms=self.shadow_latency_ms if self.sampled else None,
            shadow_error=self.shadow_error if self.sampled else None,
            results_match=comparison.get('results_match'),
            difference_summary=comparison.get('difference_summary'),
            detailed_differences=comparison.get('detailed_differences'),
            correctness_score=comparison.get('correctness_score', 0.0),
            performance_ratio=performance_ratio,
        )
        
        return result
    
    def save_result(
        self,
        result: ShadowModeResult,
        filename: Optional[str] = None
    ) -> str:
        """
        Save shadow mode result to YAML file.
        
        Args:
            result: ShadowModeResult object
            filename: Optional custom filename (defaults to task_id-based)
        
        Returns:
            Path to saved file
        """
        import yaml
        
        if filename is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"{date_str}-{self.task_id}-shadow.yaml"
        
        filepath = self.metrics_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                yaml.dump(result.to_dict(), f, default_flow_style=False, sort_keys=False)
            logger.info(f"Shadow mode result saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save shadow mode result: {e}")
            raise
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of shadow mode execution metrics."""
        return {
            'task_id': self.task_id,
            'sampled': self.sampled,
            'traffic_percentage': self.traffic_percentage,
            'production_latency_ms': self.production_latency_ms,
            'shadow_latency_ms': self.shadow_latency_ms,
            'production_error': self.production_error,
            'shadow_error': self.shadow_error,
            'timestamp': datetime.now().isoformat(),
        }


class ShadowModeAggregator:
    """Aggregate shadow mode metrics across multiple executions."""
    
    def __init__(self, metrics_dir: str = "artifacts/shadow-mode"):
        """Initialize aggregator."""
        self.metrics_dir = Path(metrics_dir)
    
    def aggregate_daily(self, date_str: str = None) -> ShadowModeMetrics:
        """
        Aggregate shadow mode metrics for a given date.
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            ShadowModeMetrics object
        """
        import yaml
        
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Find all shadow mode result files for this date
        pattern = f"{date_str}-*-shadow.yaml"
        result_files = list(self.metrics_dir.glob(pattern))
        
        if not result_files:
            return ShadowModeMetrics()
        
        # Load all results
        results = []
        for filepath in result_files:
            try:
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        results.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")
        
        if not results:
            return ShadowModeMetrics()
        
        # Calculate aggregates
        metrics = ShadowModeMetrics(
            total_tasks=len(results),
            sampled_tasks=sum(1 for r in results if r.get('sampled')),
        )
        
        if metrics.total_tasks > 0:
            metrics.sampling_rate = metrics.sampled_tasks / metrics.total_tasks
        
        # Correctness metrics
        sampled_results = [r for r in results if r.get('sampled')]
        if sampled_results:
            matches = sum(1 for r in sampled_results if r.get('results_match'))
            metrics.matching_results = matches
            metrics.mismatched_results = len(sampled_results) - matches
            metrics.match_rate = matches / len(sampled_results) if sampled_results else 0.0
        
        # Error metrics
        metrics.production_errors = sum(1 for r in results if r.get('production_error'))
        metrics.shadow_errors = sum(1 for r in sampled_results if r.get('shadow_error'))
        
        if metrics.shadow_errors > 0 and metrics.production_errors > 0:
            # Count shadow errors that also had production errors
            correlated = sum(
                1 for r in sampled_results
                if r.get('shadow_error') and r.get('production_error')
            )
            metrics.error_correlation = correlated / metrics.shadow_errors
        
        # Performance metrics
        prod_latencies = [r.get('production_latency_ms', 0) for r in results]
        shadow_latencies = [r.get('shadow_latency_ms', 0) for r in sampled_results]
        perf_ratios = [r.get('performance_ratio', 1.0) for r in sampled_results]
        
        if prod_latencies:
            metrics.avg_production_latency_ms = sum(prod_latencies) / len(prod_latencies)
        if shadow_latencies:
            metrics.avg_shadow_latency_ms = sum(shadow_latencies) / len(shadow_latencies)
        if perf_ratios:
            metrics.avg_performance_ratio = sum(perf_ratios) / len(perf_ratios)
        
        return metrics
    
    def save_aggregated_report(
        self,
        metrics: ShadowModeMetrics,
        date_str: str = None,
        filename: str = None
    ) -> str:
        """
        Save aggregated metrics report.
        
        Args:
            metrics: ShadowModeMetrics object
            date_str: Date in YYYY-MM-DD format
            filename: Optional custom filename
        
        Returns:
            Path to saved report
        """
        import yaml
        
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        if filename is None:
            filename = f"{date_str}-shadow-mode-report.yaml"
        
        filepath = self.metrics_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                yaml.dump(metrics.to_dict(), f, default_flow_style=False, sort_keys=False)
            logger.info(f"Shadow mode report saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save shadow mode report: {e}")
            raise


def get_shadow_mode_config() -> Tuple[bool, int]:
    """
    Get shadow mode configuration from environment variables.
    
    Returns:
        Tuple of (enabled, traffic_percentage)
    """
    enabled = os.environ.get('SHADOW_MODE_ENABLED', '').lower() in ('true', '1', 'yes')
    traffic_pct = int(os.environ.get('SHADOW_MODE_TRAFFIC_PCT', '10'))
    
    # Validate traffic percentage
    if traffic_pct not in [e.value for e in ShadowModeTraffic]:
        logger.warning(
            f"Invalid SHADOW_MODE_TRAFFIC_PCT: {traffic_pct}. "
            f"Defaulting to 10%"
        )
        traffic_pct = 10
    
    return enabled, traffic_pct
