"""
Cost tracking and budget management for Copilot harness.

Provides comprehensive token usage tracking, cost calculation, and budget management
for AI model invocations across different pricing tiers.

Author: Engineer
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class TokenUsage:
    """Represents token usage for a single task or session."""
    
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output + cached)."""
        return self.input_tokens + self.output_tokens + self.cached_tokens


@dataclass
class TaskCost:
    """Represents cost and usage for a single task."""
    
    task_id: str
    model: str
    timestamp: datetime
    token_usage: TokenUsage
    cost_usd: float
    duration_ms: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class PricingTier:
    """Pricing configuration for a model tier."""
    
    model: str
    input_cost_per_mtok: float  # Cost per million input tokens
    output_cost_per_mtok: float  # Cost per million output tokens
    cached_cost_per_mtok: float  # Cost per million cached tokens (typically 10% of input)


class PricingTable:
    """Central pricing table for all supported models."""
    
    DEFAULT_PRICING = {
        # Tier 1 (Haiku) - Cheap
        "claude-haiku-4.5": PricingTier(
            model="claude-haiku-4.5",
            input_cost_per_mtok=0.80,      # $0.80 per million input tokens
            output_cost_per_mtok=4.00,     # $4.00 per million output tokens
            cached_cost_per_mtok=0.08,     # 10% of input cost
        ),
        # Tier 2 (Sonnet) - Medium
        "claude-sonnet-4.6": PricingTier(
            model="claude-sonnet-4.6",
            input_cost_per_mtok=3.00,      # $3.00 per million input tokens
            output_cost_per_mtok=15.00,    # $15.00 per million output tokens
            cached_cost_per_mtok=0.30,     # 10% of input cost
        ),
        # Tier 3 (Opus) - Premium
        "claude-opus-4-6": PricingTier(
            model="claude-opus-4-6",
            input_cost_per_mtok=15.00,     # $15.00 per million input tokens
            output_cost_per_mtok=75.00,    # $75.00 per million output tokens
            cached_cost_per_mtok=1.50,     # 10% of input cost
        ),
        "claude-opus-4.8": PricingTier(
            model="claude-opus-4.8",
            input_cost_per_mtok=15.00,     # $15.00 per million input tokens
            output_cost_per_mtok=75.00,    # $75.00 per million output tokens
            cached_cost_per_mtok=1.50,     # 10% of input cost
        ),
    }
    
    def __init__(self, custom_pricing: Optional[Dict[str, PricingTier]] = None):
        """
        Initialize pricing table.
        
        Args:
            custom_pricing: Optional custom pricing dictionary to override defaults.
        """
        self.pricing = self.DEFAULT_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)
    
    def get_pricing(self, model: str) -> Optional[PricingTier]:
        """Get pricing tier for a model."""
        return self.pricing.get(model)
    
    def calculate_cost(self, model: str, token_usage: TokenUsage) -> float:
        """
        Calculate cost for token usage on a given model.
        
        Args:
            model: Model identifier
            token_usage: Token usage breakdown
            
        Returns:
            Cost in USD, or 0.0 if model not found
        """
        pricing = self.get_pricing(model)
        if not pricing:
            return 0.0
        
        input_cost = (token_usage.input_tokens / 1_000_000) * pricing.input_cost_per_mtok
        output_cost = (token_usage.output_tokens / 1_000_000) * pricing.output_cost_per_mtok
        cached_cost = (token_usage.cached_tokens / 1_000_000) * pricing.cached_cost_per_mtok
        
        return input_cost + output_cost + cached_cost


class CostTracker:
    """
    Tracks token usage and costs for tasks and sessions.
    
    Provides per-task cost tracking, session cumulative spending,
    budget management, and cost forecasting capabilities.
    """
    
    def __init__(
        self,
        pricing_table: Optional[PricingTable] = None,
        session_id: str = "",
    ):
        """
        Initialize cost tracker.
        
        Args:
            pricing_table: Custom pricing table (uses default if not provided)
            session_id: Optional session identifier for grouping costs
        """
        self.pricing_table = pricing_table or PricingTable()
        self.session_id = session_id or datetime.now().isoformat()
        self.tasks: List[TaskCost] = []
        self.session_start = datetime.now()
        
    def record_task(
        self,
        task_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        duration_ms: int = 0,
        metadata: Optional[Dict] = None,
    ) -> TaskCost:
        """
        Record a task's token usage and calculate cost.
        
        Args:
            task_id: Unique task identifier
            model: Model used for the task
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens
            duration_ms: Task execution duration in milliseconds
            metadata: Optional additional metadata
            
        Returns:
            TaskCost record
        """
        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
        )
        
        cost = self.pricing_table.calculate_cost(model, token_usage)
        
        task_cost = TaskCost(
            task_id=task_id,
            model=model,
            timestamp=datetime.now(),
            token_usage=token_usage,
            cost_usd=cost,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        
        self.tasks.append(task_cost)
        return task_cost
    
    def get_task_cost(self, task_id: str) -> Optional[TaskCost]:
        """Get cost record for a specific task."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def get_session_total_cost(self) -> float:
        """Get total cost for the entire session."""
        return sum(task.cost_usd for task in self.tasks)
    
    def get_session_total_tokens(self) -> TokenUsage:
        """Get total token usage for the session."""
        total = TokenUsage()
        for task in self.tasks:
            total.input_tokens += task.token_usage.input_tokens
            total.output_tokens += task.token_usage.output_tokens
            total.cached_tokens += task.token_usage.cached_tokens
        return total
    
    def get_cost_by_model(self) -> Dict[str, Dict]:
        """
        Get cost breakdown by model.
        
        Returns:
            Dictionary mapping model names to {cost, count, tokens}
        """
        breakdown: Dict[str, Dict] = defaultdict(lambda: {
            "cost": 0.0,
            "count": 0,
            "tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        })
        
        for task in self.tasks:
            breakdown[task.model]["cost"] += task.cost_usd
            breakdown[task.model]["count"] += 1
            breakdown[task.model]["tokens"] += task.token_usage.total_tokens
            breakdown[task.model]["input_tokens"] += task.token_usage.input_tokens
            breakdown[task.model]["output_tokens"] += task.token_usage.output_tokens
        
        return dict(breakdown)
    
    def get_cost_by_hour(self) -> Dict[str, float]:
        """
        Get hourly cost breakdown.
        
        Returns:
            Dictionary mapping hour timestamps to costs
        """
        hourly: Dict[str, float] = defaultdict(float)
        
        for task in self.tasks:
            hour_key = task.timestamp.strftime("%Y-%m-%d %H:00:00")
            hourly[hour_key] += task.cost_usd
        
        return dict(hourly)
    
    def get_average_cost_per_task(self) -> float:
        """Get average cost per task."""
        if not self.tasks:
            return 0.0
        return self.get_session_total_cost() / len(self.tasks)
    
    def get_average_tokens_per_task(self) -> int:
        """Get average tokens per task."""
        if not self.tasks:
            return 0
        total_tokens = self.get_session_total_tokens().total_tokens
        return total_tokens // len(self.tasks) if self.tasks else 0
    
    def get_tasks_by_model(self, model: str) -> List[TaskCost]:
        """Get all tasks using a specific model."""
        return [task for task in self.tasks if task.model == model]
    
    def get_most_expensive_tasks(self, limit: int = 10) -> List[TaskCost]:
        """Get the most expensive tasks."""
        sorted_tasks = sorted(self.tasks, key=lambda t: t.cost_usd, reverse=True)
        return sorted_tasks[:limit]
    
    def get_efficiency_ratio(self) -> float:
        """
        Calculate efficiency ratio (useful output tokens / total tokens).
        
        A higher ratio indicates better cache hit and output efficiency.
        """
        total = self.get_session_total_tokens()
        if total.total_tokens == 0:
            return 0.0
        
        # Output tokens are "useful" (they're the actual response)
        # Cached tokens reduce costs but don't increase usefulness
        useful = total.output_tokens
        return useful / total.total_tokens
    
    def export_to_json(self) -> str:
        """Export session data to JSON format."""
        tasks_data = [
            {
                "task_id": task.task_id,
                "model": task.model,
                "timestamp": task.timestamp.isoformat(),
                "input_tokens": task.token_usage.input_tokens,
                "output_tokens": task.token_usage.output_tokens,
                "cached_tokens": task.token_usage.cached_tokens,
                "total_tokens": task.token_usage.total_tokens,
                "cost_usd": task.cost_usd,
                "duration_ms": task.duration_ms,
                "metadata": task.metadata,
            }
            for task in self.tasks
        ]
        
        total_tokens = self.get_session_total_tokens()
        
        return json.dumps({
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat(),
            "session_duration_ms": int((datetime.now() - self.session_start).total_seconds() * 1000),
            "total_tasks": len(self.tasks),
            "total_cost_usd": self.get_session_total_cost(),
            "total_input_tokens": total_tokens.input_tokens,
            "total_output_tokens": total_tokens.output_tokens,
            "total_cached_tokens": total_tokens.cached_tokens,
            "total_tokens": total_tokens.total_tokens,
            "average_cost_per_task": self.get_average_cost_per_task(),
            "average_tokens_per_task": self.get_average_tokens_per_task(),
            "efficiency_ratio": self.get_efficiency_ratio(),
            "cost_by_model": self.get_cost_by_model(),
            "tasks": tasks_data,
        }, indent=2)
    
    def save_to_file(self, filepath: Union[Path, str]) -> None:
        """Save session data to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.export_to_json())
    
    def load_from_file(self, filepath: Union[Path, str]) -> None:
        """Load session data from JSON file."""
        filepath = Path(filepath)
        data = json.loads(filepath.read_text())
        
        self.session_id = data.get("session_id", self.session_id)
        
        # Reconstruct tasks from JSON
        for task_data in data.get("tasks", []):
            token_usage = TokenUsage(
                input_tokens=task_data["input_tokens"],
                output_tokens=task_data["output_tokens"],
                cached_tokens=task_data["cached_tokens"],
            )
            
            task = TaskCost(
                task_id=task_data["task_id"],
                model=task_data["model"],
                timestamp=datetime.fromisoformat(task_data["timestamp"]),
                token_usage=token_usage,
                cost_usd=task_data["cost_usd"],
                duration_ms=task_data["duration_ms"],
                metadata=task_data.get("metadata", {}),
            )
            self.tasks.append(task)
