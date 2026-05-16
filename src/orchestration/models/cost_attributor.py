# -*- coding: utf-8 -*-
"""
CostAttributor — Allocate task costs by role, model, task type, and time period.

Implements weighted cost attribution based on token contribution:
  - Input: task_id, agents, tokens_per_agent, total_cost
  - Output: cost_per_agent (weighted by tokens)
  - Handles edge cases (zero tokens, single agent, etc.)

Attribution dimensions:
  - Agent/Role (Engineer, Senior Engineer, etc.)
  - Model (Haiku, Sonnet, Opus)
  - Task Type (routing, implementation, review, etc.)
  - Time Period (hourly, daily, weekly)

Example:
    attributor = CostAttributor()
    result = attributor.attribute_cost(
        task_id="task-001",
        agents=["engineer", "senior_engineer"],
        tokens_per_agent={"engineer": 10000, "senior_engineer": 20000},
        total_cost=0.45,
    )
    # result = {
    #     "engineer": 0.15,
    #     "senior_engineer": 0.30,
    # }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AgentCostShare:
    """Cost allocation for a single agent in a task."""
    agent: str
    role: str
    model: str
    tokens: int
    cost: float
    weight: float  # token contribution as fraction of total
    task_type: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class CostAttributionResult:
    """Result of cost attribution for a task."""
    task_id: str
    total_cost: float
    total_tokens: int
    timestamp: str
    agent_shares: Dict[str, AgentCostShare] = field(default_factory=dict)
    
    def summary(self) -> str:
        """Return human-readable summary of cost attribution."""
        lines = [
            f"Cost Attribution: {self.task_id}",
            f"  Total cost: ${self.total_cost:.4f}",
            f"  Total tokens: {self.total_tokens:,}",
            f"  Timestamp: {self.timestamp}",
            "",
            "Agent shares:",
        ]
        for agent, share in sorted(self.agent_shares.items()):
            lines.append(
                f"  {agent} [{share.role}/{share.model}]: "
                f"${share.cost:.4f} ({share.weight*100:.1f}%) "
                f"({share.tokens:,} tokens)"
            )
        return "\n".join(lines)


@dataclass
class DimensionalCosts:
    """Costs aggregated by different dimensions."""
    by_role: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    by_task_type: Dict[str, float] = field(default_factory=dict)
    by_date: Dict[str, float] = field(default_factory=dict)
    
    def add_cost(
        self,
        cost: float,
        role: Optional[str] = None,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        date: Optional[str] = None,
    ) -> None:
        """Add cost to all applicable dimensions."""
        if role:
            self.by_role[role] = self.by_role.get(role, 0.0) + cost
        if model:
            self.by_model[model] = self.by_model.get(model, 0.0) + cost
        if task_type:
            self.by_task_type[task_type] = self.by_task_type.get(task_type, 0.0) + cost
        if date:
            self.by_date[date] = self.by_date.get(date, 0.0) + cost


# ---------------------------------------------------------------------------
# CostAttributor
# ---------------------------------------------------------------------------

class CostAttributor:
    """
    Allocate task costs to agents based on token contribution.
    
    Thread-safe for concurrent attribution operations.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._attribution_history: List[CostAttributionResult] = []
    
    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------
    
    def attribute_cost(
        self,
        task_id: str,
        agents: List[str],
        tokens_per_agent: Dict[str, int],
        total_cost: float,
        roles_per_agent: Optional[Dict[str, str]] = None,
        models_per_agent: Optional[Dict[str, str]] = None,
        task_type: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> CostAttributionResult:
        """
        Allocate task cost to agents based on token contribution.
        
        Args:
            task_id: Unique task identifier
            agents: List of agent names
            tokens_per_agent: Dict mapping agent name to token count
            total_cost: Total task cost in USD
            roles_per_agent: Optional dict mapping agent to role (e.g., "engineer")
            models_per_agent: Optional dict mapping agent to model (e.g., "sonnet-4-6")
            task_type: Optional task type (e.g., "implementation", "review")
            timestamp: Optional ISO8601 timestamp (defaults to now)
        
        Returns:
            CostAttributionResult with cost shares for each agent
        
        Raises:
            ValueError: If agents list is empty, tokens are all zero, or cost is negative
        """
        # Validate inputs
        if not agents:
            raise ValueError("agents list cannot be empty")
        if total_cost < 0:
            raise ValueError(f"total_cost must be non-negative, got {total_cost}")
        
        # Handle missing optional dicts
        if roles_per_agent is None:
            roles_per_agent = {agent: "unknown" for agent in agents}
        if models_per_agent is None:
            models_per_agent = {agent: "unknown" for agent in agents}
        
        # Set timestamp
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Calculate total tokens
        total_tokens = sum(tokens_per_agent.get(agent, 0) for agent in agents)
        
        # Handle edge case: no tokens consumed
        if total_tokens == 0:
            # Distribute cost equally
            cost_per_agent = total_cost / len(agents) if agents else 0.0
            shares = {}
            for agent in agents:
                shares[agent] = AgentCostShare(
                    agent=agent,
                    role=roles_per_agent.get(agent, "unknown"),
                    model=models_per_agent.get(agent, "unknown"),
                    tokens=0,
                    cost=cost_per_agent,
                    weight=1.0 / len(agents) if agents else 0.0,
                    task_type=task_type,
                    timestamp=timestamp,
                )
            result = CostAttributionResult(
                task_id=task_id,
                total_cost=total_cost,
                total_tokens=0,
                timestamp=timestamp,
                agent_shares=shares,
            )
        else:
            # Distribute cost proportionally by tokens
            shares = {}
            for agent in agents:
                tokens = tokens_per_agent.get(agent, 0)
                weight = tokens / total_tokens
                cost = total_cost * weight
                
                shares[agent] = AgentCostShare(
                    agent=agent,
                    role=roles_per_agent.get(agent, "unknown"),
                    model=models_per_agent.get(agent, "unknown"),
                    tokens=tokens,
                    cost=cost,
                    weight=weight,
                    task_type=task_type,
                    timestamp=timestamp,
                )
            
            result = CostAttributionResult(
                task_id=task_id,
                total_cost=total_cost,
                total_tokens=total_tokens,
                timestamp=timestamp,
                agent_shares=shares,
            )
        
        # Record in history
        with self._lock:
            self._attribution_history.append(result)
        
        return result
    
    # ------------------------------------------------------------------
    # Aggregation API
    # ------------------------------------------------------------------
    
    def aggregate_by_dimensions(
        self,
        results: List[CostAttributionResult],
    ) -> DimensionalCosts:
        """
        Aggregate costs from multiple attribution results by dimensions.
        
        Args:
            results: List of CostAttributionResult objects
        
        Returns:
            DimensionalCosts with aggregated costs by role, model, task_type, date
        """
        dimensional = DimensionalCosts()
        
        for result in results:
            for agent, share in result.agent_shares.items():
                # Extract date from timestamp (YYYY-MM-DD)
                date = share.timestamp[:10] if share.timestamp else None
                
                dimensional.add_cost(
                    cost=share.cost,
                    role=share.role,
                    model=share.model,
                    task_type=share.task_type,
                    date=date,
                )
        
        return dimensional
    
    def aggregate_by_role(
        self,
        results: List[CostAttributionResult],
    ) -> Dict[str, float]:
        """Aggregate total cost by role."""
        by_role: Dict[str, float] = {}
        for result in results:
            for agent, share in result.agent_shares.items():
                role = share.role
                by_role[role] = by_role.get(role, 0.0) + share.cost
        return by_role
    
    def aggregate_by_model(
        self,
        results: List[CostAttributionResult],
    ) -> Dict[str, float]:
        """Aggregate total cost by model."""
        by_model: Dict[str, float] = {}
        for result in results:
            for agent, share in result.agent_shares.items():
                model = share.model
                by_model[model] = by_model.get(model, 0.0) + share.cost
        return by_model
    
    def aggregate_by_task_type(
        self,
        results: List[CostAttributionResult],
    ) -> Dict[str, float]:
        """Aggregate total cost by task type."""
        by_task_type: Dict[str, float] = {}
        for result in results:
            for agent, share in result.agent_shares.items():
                if share.task_type:
                    task_type = share.task_type
                    by_task_type[task_type] = by_task_type.get(task_type, 0.0) + share.cost
        return by_task_type
    
    def aggregate_by_date(
        self,
        results: List[CostAttributionResult],
    ) -> Dict[str, float]:
        """Aggregate total cost by date (YYYY-MM-DD)."""
        by_date: Dict[str, float] = {}
        for result in results:
            for agent, share in result.agent_shares.items():
                if share.timestamp:
                    date = share.timestamp[:10]
                    by_date[date] = by_date.get(date, 0.0) + share.cost
        return by_date
    
    # ------------------------------------------------------------------
    # History API
    # ------------------------------------------------------------------
    
    def get_history(self) -> List[CostAttributionResult]:
        """Return all attribution results in history."""
        with self._lock:
            return list(self._attribution_history)
    
    def clear_history(self) -> None:
        """Clear attribution history (for testing)."""
        with self._lock:
            self._attribution_history.clear()
    
    def get_task_attribution(self, task_id: str) -> Optional[CostAttributionResult]:
        """Retrieve attribution result for a specific task."""
        with self._lock:
            for result in self._attribution_history:
                if result.task_id == task_id:
                    return result
        return None
    
    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    
    @staticmethod
    def calculate_weight(tokens: int, total_tokens: int) -> float:
        """Calculate weight as fraction of total tokens."""
        if total_tokens == 0:
            return 0.0
        return tokens / total_tokens
    
    @staticmethod
    def allocate_cost(weight: float, total_cost: float) -> float:
        """Allocate cost based on weight."""
        return weight * total_cost
