"""
Rate Limiter — Enforce rate limits on sub-agent invocations.

Prevents excessive delegation requests that could cause resource exhaustion
or indicate compromised components.
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiting for agent invocations.
    
    Supports:
    - Per-agent rate limits (e.g., orchestrator max 100/hour)
    - Per-role rate limits (e.g., engineers max 10/minute)
    - Configurable thresholds and windows
    - Token-bucket algorithm
    """
    
    # Default rate limits
    DEFAULT_AGENT_LIMITS = {
        'orchestrator': {'calls_per_minute': 100, 'calls_per_hour': 1000},
        'engineer': {'calls_per_minute': 10, 'calls_per_hour': 100},
        'senior_engineer': {'calls_per_minute': 15, 'calls_per_hour': 150},
        'lead_engineer': {'calls_per_minute': 20, 'calls_per_hour': 200},
        'principal_engineer': {'calls_per_minute': 10, 'calls_per_hour': 100},
        'security_engineer': {'calls_per_minute': 5, 'calls_per_hour': 50},
        'quality_engineer': {'calls_per_minute': 10, 'calls_per_hour': 100},
        'model_engineer': {'calls_per_minute': 10, 'calls_per_hour': 100},
    }
    
    def __init__(self):
        """Initialize rate limiter."""
        self.call_history: Dict[str, list] = defaultdict(list)  # agent_id -> [timestamps]
        self.limits = self.DEFAULT_AGENT_LIMITS.copy()
    
    def set_limit(self, agent_role: str, calls_per_minute: int, 
                 calls_per_hour: int) -> None:
        """
        Set rate limits for an agent role.
        
        Args:
            agent_role: Agent role (orchestrator, engineer, etc.)
            calls_per_minute: Maximum calls in 60 seconds
            calls_per_hour: Maximum calls in 3600 seconds
        """
        self.limits[agent_role] = {
            'calls_per_minute': calls_per_minute,
            'calls_per_hour': calls_per_hour,
        }
    
    def check_rate_limit(self, agent_id: str, agent_role: str) -> tuple:
        """
        Check if agent has exceeded rate limit.
        
        Args:
            agent_id: Unique agent identifier
            agent_role: Agent role
            
        Returns:
            (is_allowed, reason, retry_after_seconds)
        """
        now = time.time()
        
        # Get limits for this role
        limits = self.limits.get(agent_role, self.DEFAULT_AGENT_LIMITS.get('engineer'))
        if not limits:
            return True, None, None  # No limit defined
        
        # Clean old entries (older than 1 hour)
        one_hour_ago = now - 3600
        self.call_history[agent_id] = [ts for ts in self.call_history[agent_id] 
                                       if ts > one_hour_ago]
        
        # Check per-minute limit
        minute_ago = now - 60
        calls_in_minute = len([ts for ts in self.call_history[agent_id] 
                              if ts > minute_ago])
        
        if calls_in_minute >= limits['calls_per_minute']:
            next_window = min(self.call_history[agent_id]) + 60
            retry_after = int(next_window - now) + 1
            return False, f"Rate limit exceeded: {calls_in_minute}/{limits['calls_per_minute']} calls/min", retry_after
        
        # Check per-hour limit
        calls_in_hour = len(self.call_history[agent_id])
        
        if calls_in_hour >= limits['calls_per_hour']:
            next_window = min(self.call_history[agent_id]) + 3600
            retry_after = int(next_window - now) + 1
            return False, f"Rate limit exceeded: {calls_in_hour}/{limits['calls_per_hour']} calls/hour", retry_after
        
        # Record this call
        self.call_history[agent_id].append(now)
        
        return True, None, None
    
    def record_call(self, agent_id: str) -> None:
        """Record a successful call from an agent."""
        self.call_history[agent_id].append(time.time())
    
    def get_stats(self, agent_id: str, agent_role: str) -> Dict[str, any]:
        """
        Get rate limit statistics for an agent.
        
        Returns:
            Dictionary with current usage, limits, and headroom
        """
        now = time.time()
        
        # Clean old entries
        one_hour_ago = now - 3600
        self.call_history[agent_id] = [ts for ts in self.call_history[agent_id] 
                                       if ts > one_hour_ago]
        
        limits = self.limits.get(agent_role, self.DEFAULT_AGENT_LIMITS.get('engineer'))
        
        minute_ago = now - 60
        calls_in_minute = len([ts for ts in self.call_history[agent_id] 
                              if ts > minute_ago])
        calls_in_hour = len(self.call_history[agent_id])
        
        return {
            'agent_id': agent_id,
            'agent_role': agent_role,
            'calls_in_minute': calls_in_minute,
            'limit_per_minute': limits['calls_per_minute'],
            'headroom_minute': limits['calls_per_minute'] - calls_in_minute,
            'calls_in_hour': calls_in_hour,
            'limit_per_hour': limits['calls_per_hour'],
            'headroom_hour': limits['calls_per_hour'] - calls_in_hour,
        }


class BudgetEnforcer:
    """
    Enforce token budget limits per agent per time period.
    
    Tracks token spending and enforces hard limits to prevent
    runaway token consumption.
    """
    
    # Default budgets (tokens per period)
    DEFAULT_BUDGETS = {
        'orchestrator': {'per_day': 500000, 'per_week': 2000000, 'per_month': 8000000},
        'engineer': {'per_day': 100000, 'per_week': 400000, 'per_month': 1600000},
        'senior_engineer': {'per_day': 200000, 'per_week': 800000, 'per_month': 3200000},
        'lead_engineer': {'per_day': 150000, 'per_week': 600000, 'per_month': 2400000},
        'principal_engineer': {'per_day': 250000, 'per_week': 1000000, 'per_month': 4000000},
        'security_engineer': {'per_day': 80000, 'per_week': 320000, 'per_month': 1280000},
        'quality_engineer': {'per_day': 80000, 'per_week': 320000, 'per_month': 1280000},
        'model_engineer': {'per_day': 150000, 'per_week': 600000, 'per_month': 2400000},
    }
    
    def __init__(self):
        """Initialize budget enforcer."""
        self.spending: Dict[str, list] = defaultdict(list)  # agent_id -> [{timestamp, tokens}, ...]
        self.budgets = {}
        
        # Initialize with defaults
        for role, budgets in self.DEFAULT_BUDGETS.items():
            self.budgets[role] = budgets.copy()
    
    def set_budget(self, agent_role: str, per_day: int, per_week: int, 
                  per_month: int) -> None:
        """Set token budget for an agent role."""
        self.budgets[agent_role] = {
            'per_day': per_day,
            'per_week': per_week,
            'per_month': per_month,
        }
    
    def check_budget(self, agent_id: str, agent_role: str, 
                    tokens_to_spend: int) -> tuple:
        """
        Check if agent can spend tokens without exceeding budget.
        
        Args:
            agent_id: Unique agent identifier
            agent_role: Agent role
            tokens_to_spend: Number of tokens to spend
            
        Returns:
            (is_allowed, reason, tokens_until_limit)
        """
        now = time.time()
        
        # Clean old entries
        day_ago = now - 86400
        self.spending[agent_id] = [entry for entry in self.spending[agent_id]
                                   if entry['timestamp'] > day_ago]
        
        budgets = self.budgets.get(agent_role, self.DEFAULT_BUDGETS.get('engineer'))
        if not budgets:
            return True, None, None  # No budget defined
        
        # Calculate spending in each period
        week_ago = now - 604800  # 7 days
        month_ago = now - 2592000  # 30 days
        
        spend_today = sum(entry['tokens'] for entry in self.spending[agent_id]
                         if entry['timestamp'] > day_ago)
        spend_week = sum(entry['tokens'] for entry in self.spending[agent_id]
                        if entry['timestamp'] > week_ago)
        spend_month = sum(entry['tokens'] for entry in self.spending[agent_id]
                         if entry['timestamp'] > month_ago)
        
        # Check limits
        if spend_today + tokens_to_spend > budgets['per_day']:
            remaining = budgets['per_day'] - spend_today
            return False, f"Daily budget exceeded: {spend_today}/{budgets['per_day']}", remaining
        
        if spend_week + tokens_to_spend > budgets['per_week']:
            remaining = budgets['per_week'] - spend_week
            return False, f"Weekly budget exceeded: {spend_week}/{budgets['per_week']}", remaining
        
        if spend_month + tokens_to_spend > budgets['per_month']:
            remaining = budgets['per_month'] - spend_month
            return False, f"Monthly budget exceeded: {spend_month}/{budgets['per_month']}", remaining
        
        return True, None, min(
            budgets['per_day'] - spend_today,
            budgets['per_week'] - spend_week,
            budgets['per_month'] - spend_month
        )
    
    def record_spending(self, agent_id: str, tokens: int) -> None:
        """Record token spending for an agent."""
        self.spending[agent_id].append({
            'timestamp': time.time(),
            'tokens': tokens,
        })
    
    def get_spending(self, agent_id: str, agent_role: str) -> Dict[str, any]:
        """Get spending statistics for an agent."""
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800
        month_ago = now - 2592000
        
        # Clean old entries
        self.spending[agent_id] = [entry for entry in self.spending[agent_id]
                                   if entry['timestamp'] > month_ago]
        
        budgets = self.budgets.get(agent_role, self.DEFAULT_BUDGETS.get('engineer'))
        
        spend_today = sum(entry['tokens'] for entry in self.spending[agent_id]
                         if entry['timestamp'] > day_ago)
        spend_week = sum(entry['tokens'] for entry in self.spending[agent_id]
                        if entry['timestamp'] > week_ago)
        spend_month = sum(entry['tokens'] for entry in self.spending[agent_id]
                         if entry['timestamp'] > month_ago)
        
        return {
            'agent_id': agent_id,
            'agent_role': agent_role,
            'tokens_today': spend_today,
            'budget_per_day': budgets['per_day'],
            'pct_of_daily_budget': int(100 * spend_today / budgets['per_day']),
            'tokens_week': spend_week,
            'budget_per_week': budgets['per_week'],
            'pct_of_weekly_budget': int(100 * spend_week / budgets['per_week']),
            'tokens_month': spend_month,
            'budget_per_month': budgets['per_month'],
            'pct_of_monthly_budget': int(100 * spend_month / budgets['per_month']),
        }
