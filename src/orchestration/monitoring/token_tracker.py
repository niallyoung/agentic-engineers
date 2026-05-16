"""
Token Tracker — Parse token-aggregator plugin output and track token metrics.

Provides visibility into token consumption across agents, with cost attribution
based on weighted token contribution. Integrates with MetricsRegistry for
real-time metrics collection.

Usage:
    tracker = TokenTracker(registry)
    tracker.record_task_tokens(
        task_id="task-123",
        agent="engineer",
        input_tokens=1000,
        output_tokens=500,
        cached_tokens=100,
        cost_usd=0.045
    )
    
    # Get aggregated metrics
    stats = tracker.get_stats()
"""

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .metrics import MetricsRegistry, Counter, Histogram


@dataclass
class TokenMetrics:
    """Token metrics for a single task."""
    task_id: str
    agent: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens consumed (input + output + cached)."""
        return self.input_tokens + self.output_tokens + self.cached_tokens
    
    @property
    def effective_tokens(self) -> int:
        """Effective tokens (input + output, cached doesn't count toward limit)."""
        return self.input_tokens + self.output_tokens


@dataclass
class TokenStats:
    """Aggregated token statistics."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_cost_usd: float = 0.0
    task_count: int = 0
    agent_tokens: Dict[str, int] = field(default_factory=dict)
    agent_costs: Dict[str, float] = field(default_factory=dict)
    agent_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens consumed."""
        return self.total_input_tokens + self.total_output_tokens + self.total_cached_tokens
    
    @property
    def effective_tokens(self) -> int:
        """Effective tokens (excluding cached)."""
        return self.total_input_tokens + self.total_output_tokens
    
    @property
    def avg_cost_per_task(self) -> float:
        """Average cost per task."""
        if self.task_count == 0:
            return 0.0
        return self.total_cost_usd / self.task_count
    
    @property
    def avg_tokens_per_task(self) -> float:
        """Average tokens per task."""
        if self.task_count == 0:
            return 0.0
        return self.effective_tokens / self.task_count


class TokenTracker:
    """
    Tracks token usage and cost attribution across tasks and agents.
    
    Thread-safe implementation that records token metrics from task execution
    and maintains aggregated statistics. Integrates with MetricsRegistry to
    expose metrics for monitoring and alerting.
    """
    
    def __init__(self, registry: MetricsRegistry):
        """
        Initialize TokenTracker with a MetricsRegistry.
        
        Args:
            registry: MetricsRegistry instance for metric registration
        """
        self.registry = registry
        self._lock = threading.Lock()
        self._metrics: List[TokenMetrics] = []
        self._agent_totals: Dict[str, Dict[str, int]] = {}
        
        # Register token metrics
        self._setup_metrics()
    
    def _setup_metrics(self) -> None:
        """Register all token-related metrics with the registry."""
        # Counters for cumulative token tracking
        self.tokens_input_total = self.registry.counter(
            "orchestrator_tokens_input_total",
            "Total input tokens consumed across all tasks",
        )
        self.tokens_output_total = self.registry.counter(
            "orchestrator_tokens_output_total",
            "Total output tokens consumed across all tasks",
        )
        self.tokens_cached_total = self.registry.counter(
            "orchestrator_tokens_cached_total",
            "Total cached tokens read across all tasks",
        )
        self.cost_usd_total = self.registry.counter(
            "orchestrator_cost_usd_total",
            "Total cost in USD across all tasks",
        )
        
        # Histograms for per-task distributions
        self.tokens_per_task = self.registry.histogram(
            "orchestrator_tokens_per_task",
            "Distribution of tokens consumed per task",
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000],
        )
        self.cost_per_task = self.registry.histogram(
            "orchestrator_cost_per_task",
            "Distribution of cost per task in USD",
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
        )
        
        # Per-agent counters
        self.tokens_by_agent = {}  # Dict[agent, Counter]
        self.cost_by_agent = {}    # Dict[agent, Counter]
    
    def record_task_tokens(
        self,
        task_id: str,
        agent: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """
        Record token metrics for a completed task.
        
        Args:
            task_id: Unique task identifier
            agent: Agent that executed the task (e.g., "engineer", "orchestrator")
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            cached_tokens: Number of cached tokens read (optional)
            cost_usd: Cost in USD for this task (optional)
        
        Raises:
            ValueError: If any token count is negative
        """
        if input_tokens < 0 or output_tokens < 0 or cached_tokens < 0:
            raise ValueError("Token counts must be non-negative")
        if cost_usd < 0:
            raise ValueError("Cost must be non-negative")
        
        metrics = TokenMetrics(
            task_id=task_id,
            agent=agent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
        )
        
        with self._lock:
            self._metrics.append(metrics)
            
            # Update agent totals
            if agent not in self._agent_totals:
                self._agent_totals[agent] = {
                    "input": 0,
                    "output": 0,
                    "cached": 0,
                    "cost": 0.0,
                    "count": 0,
                }
            
            self._agent_totals[agent]["input"] += input_tokens
            self._agent_totals[agent]["output"] += output_tokens
            self._agent_totals[agent]["cached"] += cached_tokens
            self._agent_totals[agent]["cost"] += cost_usd
            self._agent_totals[agent]["count"] += 1
        
        # Update global counters
        self.tokens_input_total.inc(input_tokens)
        self.tokens_output_total.inc(output_tokens)
        self.tokens_cached_total.inc(cached_tokens)
        self.cost_usd_total.inc(cost_usd)
        
        # Record in histograms
        self.tokens_per_task.observe(metrics.effective_tokens)
        self.cost_per_task.observe(cost_usd)
        
        # Update per-agent metrics
        self._update_agent_metrics(agent, input_tokens, output_tokens, cost_usd)
    
    def _update_agent_metrics(
        self,
        agent: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Update per-agent counters."""
        if agent not in self.tokens_by_agent:
            self.tokens_by_agent[agent] = self.registry.counter(
                f"orchestrator_tokens_by_agent_total",
                f"Total tokens consumed by {agent}",
                labels={"agent": agent},
            )
            self.cost_by_agent[agent] = self.registry.counter(
                f"orchestrator_cost_by_agent_total",
                f"Total cost for {agent} in USD",
                labels={"agent": agent},
            )
        
        self.tokens_by_agent[agent].inc(input_tokens + output_tokens)
        self.cost_by_agent[agent].inc(cost_usd)
    
    def get_stats(self) -> TokenStats:
        """
        Get aggregated token statistics.
        
        Returns:
            TokenStats object with aggregated metrics
        """
        with self._lock:
            stats = TokenStats()
            
            for metrics in self._metrics:
                stats.total_input_tokens += metrics.input_tokens
                stats.total_output_tokens += metrics.output_tokens
                stats.total_cached_tokens += metrics.cached_tokens
                stats.total_cost_usd += metrics.cost_usd
                stats.task_count += 1
                
                # Per-agent aggregation
                agent = metrics.agent
                if agent not in stats.agent_tokens:
                    stats.agent_tokens[agent] = 0
                    stats.agent_costs[agent] = 0.0
                    stats.agent_counts[agent] = 0
                
                stats.agent_tokens[agent] += metrics.effective_tokens
                stats.agent_costs[agent] += metrics.cost_usd
                stats.agent_counts[agent] += 1
            
            return stats
    
    def get_agent_stats(self, agent: str) -> Optional[Dict[str, any]]:
        """
        Get statistics for a specific agent.
        
        Args:
            agent: Agent name
        
        Returns:
            Dict with agent statistics or None if agent not found
        """
        with self._lock:
            if agent not in self._agent_totals:
                return None
            
            totals = self._agent_totals[agent]
            return {
                "agent": agent,
                "input_tokens": totals["input"],
                "output_tokens": totals["output"],
                "cached_tokens": totals["cached"],
                "total_tokens": totals["input"] + totals["output"] + totals["cached"],
                "effective_tokens": totals["input"] + totals["output"],
                "cost_usd": totals["cost"],
                "task_count": totals["count"],
                "avg_tokens_per_task": (totals["input"] + totals["output"]) / totals["count"] if totals["count"] > 0 else 0,
                "avg_cost_per_task": totals["cost"] / totals["count"] if totals["count"] > 0 else 0,
            }
    
    def get_cost_attribution(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate cost attribution by agent based on token contribution.
        
        Returns:
            Dict mapping agent names to cost attribution details:
            {
                "agent_name": {
                    "tokens": 5000,
                    "cost": 0.05,
                    "token_percentage": 0.25,
                    "cost_percentage": 0.25,
                }
            }
        """
        stats = self.get_stats()
        
        if stats.effective_tokens == 0:
            return {}
        
        attribution = {}
        for agent, tokens in stats.agent_tokens.items():
            cost = stats.agent_costs[agent]
            token_pct = (tokens / stats.effective_tokens) * 100
            cost_pct = (cost / stats.total_cost_usd * 100) if stats.total_cost_usd > 0 else 0
            
            attribution[agent] = {
                "tokens": tokens,
                "cost": cost,
                "token_percentage": token_pct,
                "cost_percentage": cost_pct,
            }
        
        return attribution
    
    def get_all_metrics(self) -> List[TokenMetrics]:
        """
        Get all recorded token metrics.
        
        Returns:
            List of TokenMetrics objects
        """
        with self._lock:
            return list(self._metrics)
    
    def clear(self) -> None:
        """Clear all recorded metrics (for testing)."""
        with self._lock:
            self._metrics.clear()
            self._agent_totals.clear()
        
        # Reset counters
        self.tokens_input_total.reset()
        self.tokens_output_total.reset()
        self.tokens_cached_total.reset()
        self.cost_usd_total.reset()
        
        # Reset per-agent metrics
        for counter in self.tokens_by_agent.values():
            counter.reset()
        for counter in self.cost_by_agent.values():
            counter.reset()
