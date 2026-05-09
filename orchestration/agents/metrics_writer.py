"""
Metrics Writer — Persistence and aggregation of task execution metrics.

Captures and stores metrics from HANDBACK blocks for analysis by Model Engineer.
Metrics are persisted to YAML files in artifacts/metrics/ directory with
daily aggregation capabilities.

Schema Reference: Quality Engineer Section 5 (Canonical Metrics Schema)
"""

import os
import yaml
import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict, field


@dataclass
class TaskMetrics:
    """Canonical metrics structure for task execution."""
    
    # Task identity
    task_id: str
    timestamp: str  # ISO 8601 format
    role: str  # engineer, senior_engineer, etc.
    model: str  # claude-haiku-4.5, etc.
    effort: str  # low, medium, high, max, epic
    effort_actual: float  # hours actually spent
    
    # Token usage
    tokens_in: int  # input tokens consumed
    tokens_out: int  # output tokens generated
    total_tokens: int  # sum of in + out
    
    # Duration
    duration_minutes: int  # wall-clock time in minutes
    
    # Quality
    quality_score_validator: int  # authoritative validator score (0-100)
    quality_score_agent_self: int  # agent self-report for calibration (0-100)
    status: str  # complete, failed, partial, blocked
    
    # Execution context
    retry_count: int = 0  # how many retries before success/final outcome
    first_try_quality: Optional[int] = None  # quality score on first attempt if retried
    
    # Deliverables
    test_coverage: float = 0.0  # test coverage percentage
    deliverables_count: int = 0  # number of deliverables created
    
    # Derived metrics
    efficiency_score: float = 0.0  # (quality_score / tokens_used) × 100
    rework_cost_ratio: float = 1.0  # (total_tokens / estimated) — >1.0 if retried
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None fields."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class MetricsWriter:
    """Write and aggregate task metrics to YAML files."""
    
    def __init__(self, metrics_dir: str = "artifacts/metrics"):
        """Initialize metrics writer with output directory."""
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def write_metrics(self, metrics: Dict) -> str:
        """
        Write metrics to YAML file in artifacts/metrics/.
        
        File naming: YYYY-MM-DD-{task_id}-metrics.yaml
        
        Args:
            metrics: Metrics dictionary with required fields
        
        Returns:
            Path to written file
        
        Raises:
            ValueError: If required fields missing
            IOError: If file write fails
        """
        # Validate required fields
        required = {'task_id', 'timestamp', 'quality_score_validator'}
        if not required.issubset(metrics.keys()):
            missing = required - set(metrics.keys())
            raise ValueError(f"Missing required metrics fields: {missing}")
        
        # Parse timestamp to get date for filename
        try:
            ts = datetime.fromisoformat(metrics['timestamp'].replace('Z', '+00:00'))
            date_str = ts.strftime('%Y-%m-%d')
        except (ValueError, AttributeError):
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        task_id = metrics['task_id']
        filename = f"{date_str}-{task_id}-metrics.yaml"
        filepath = self.metrics_dir / filename
        
        # Write to YAML file
        try:
            with open(filepath, 'w') as f:
                yaml.dump(metrics, f, default_flow_style=False, sort_keys=False)
        except IOError as e:
            raise IOError(f"Failed to write metrics to {filepath}: {e}")
        
        return str(filepath)
    
    def load_metrics(self, task_id: str, date_str: str = None) -> Dict:
        """
        Load metrics from file.
        
        Args:
            task_id: Task identifier
            date_str: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            Parsed metrics dictionary
        
        Raises:
            FileNotFoundError: If metrics file not found
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        filename = f"{date_str}-{task_id}-metrics.yaml"
        filepath = self.metrics_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Metrics file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            metrics = yaml.safe_load(f)
        
        return metrics or {}
    
    def aggregate_metrics(self, date_str: str = None, output_file: str = None) -> Dict:
        """
        Aggregate all metrics from a given date.
        
        Calculates statistics across all tasks run on that date:
        - avg_quality_score, min_quality, max_quality
        - avg_tokens, total_tokens
        - avg_efficiency_score
        - retry_rate (tasks with retry_count > 0)
        - completion_rate (tasks with status='complete')
        
        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)
            output_file: Optional path to write aggregated report
        
        Returns:
            Dictionary with aggregated metrics
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Find all metrics files for this date
        pattern = f"{date_str}-*-metrics.yaml"
        metrics_files = list(self.metrics_dir.glob(pattern))
        
        if not metrics_files:
            return {
                'date': date_str,
                'task_count': 0,
                'timestamp': datetime.now().isoformat(),
            }
        
        # Load all metrics
        all_metrics = []
        for filepath in metrics_files:
            try:
                with open(filepath, 'r') as f:
                    metrics = yaml.safe_load(f)
                    if metrics:
                        all_metrics.append(metrics)
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")
        
        # Calculate aggregates
        if not all_metrics:
            return {
                'date': date_str,
                'task_count': 0,
                'timestamp': datetime.now().isoformat(),
            }
        
        quality_scores = [m.get('quality_score_validator', 0) for m in all_metrics]
        efficiency_scores = [m.get('efficiency_score', 0) for m in all_metrics if m.get('efficiency_score')]
        tokens_list = [m.get('total_tokens', 0) for m in all_metrics]
        retry_counts = [m.get('retry_count', 0) for m in all_metrics]
        statuses = [m.get('status', '') for m in all_metrics]
        
        aggregated = {
            'date': date_str,
            'timestamp': datetime.now().isoformat(),
            'task_count': len(all_metrics),
            'quality_score': {
                'avg': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                'min': min(quality_scores) if quality_scores else 0,
                'max': max(quality_scores) if quality_scores else 0,
            },
            'tokens': {
                'total': sum(tokens_list),
                'avg': sum(tokens_list) / len(tokens_list) if tokens_list else 0,
                'min': min(tokens_list) if tokens_list else 0,
                'max': max(tokens_list) if tokens_list else 0,
            },
            'efficiency_score': {
                'avg': sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0,
            },
            'retry_rate': sum(1 for r in retry_counts if r > 0) / len(retry_counts) if retry_counts else 0,
            'completion_rate': sum(1 for s in statuses if s == 'complete') / len(statuses) if statuses else 0,
            'tasks': [m.get('task_id') for m in all_metrics],
        }
        
        # Optionally write aggregated report
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                yaml.dump(aggregated, f, default_flow_style=False, sort_keys=False)
        
        return aggregated
