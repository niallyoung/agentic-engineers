"""
Multi-provider cost tracking and aggregation.

Tracks token usage and costs across 5 providers:
- Anthropic (Claude models)
- OpenAI (GPT models)  
- Google Gemini
- GitHub Copilot
- Ollama (local models)

Provides provider-specific metrics, aggregation, efficiency analysis,
and export capabilities.

Author: COST-002 Implementation Lead
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import json


class ProviderType(str, Enum):
    """Supported AI provider platforms."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    GITHUB_COPILOT = "github_copilot"
    OLLAMA = "ollama"


@dataclass
class TokenUsage:
    """Represents token usage for a single request."""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output + cached)."""
        return self.input_tokens + self.output_tokens + self.cached_tokens

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ProviderCost:
    """Represents a single request cost with provider-specific metrics."""
    provider: ProviderType
    model: str
    timestamp: datetime
    token_usage: TokenUsage
    cost_usd: float
    request_id: str = ""
    duration_ms: int = 0
    status: str = "success"  # success, error, timeout, etc.
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "token_usage": self.token_usage.to_dict(),
            "cost_usd": self.cost_usd,
            "request_id": self.request_id,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a single provider."""
    provider: ProviderType
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    avg_cost_per_request: float = 0.0
    avg_tokens_per_request: float = 0.0
    min_cost_per_token: float = float('inf')
    max_cost_per_token: float = 0.0
    error_rate: float = 0.0
    total_duration_ms: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens processed by this provider."""
        return self.total_input_tokens + self.total_output_tokens + self.total_cached_tokens

    @property
    def cost_per_token(self) -> float:
        """Average cost per token for this provider."""
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost_usd / self.total_tokens

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "provider": self.provider.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cached_tokens": self.total_cached_tokens,
            "total_tokens": self.total_tokens,
            "models_used": self.models_used,
            "cost_by_model": self.cost_by_model,
            "avg_cost_per_request": round(self.avg_cost_per_request, 6),
            "avg_tokens_per_request": self.avg_tokens_per_request,
            "cost_per_token": round(self.cost_per_token, 8),
            "min_cost_per_token": round(self.min_cost_per_token, 8),
            "max_cost_per_token": round(self.max_cost_per_token, 8),
            "error_rate": round(self.error_rate, 4),
            "total_duration_ms": self.total_duration_ms,
        }


class ProviderTracker:
    """
    Tracks token usage and costs across multiple AI providers.
    
    Supports 5 providers:
    - Anthropic (Claude models)
    - OpenAI (GPT models)
    - Google Gemini
    - GitHub Copilot
    - Ollama (local models)
    
    Provides per-provider metrics, aggregation, and efficiency analysis.
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize the multi-provider cost tracker."""
        self.session_id = session_id or datetime.now().isoformat()
        self.session_start = datetime.now()
        self.requests: List[ProviderCost] = []
        self._metrics: Dict[ProviderType, ProviderMetrics] = {
            provider: ProviderMetrics(provider=provider)
            for provider in ProviderType
        }

    def record_request(
        self,
        provider: ProviderType,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        request_id: str = "",
        duration_ms: int = 0,
        status: str = "success",
        cached_tokens: int = 0,
        metadata: Optional[Dict] = None,
    ) -> ProviderCost:
        """Record a single request's token usage and cost."""
        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
        )

        cost_record = ProviderCost(
            provider=provider,
            model=model,
            timestamp=datetime.now(),
            token_usage=token_usage,
            cost_usd=cost_usd,
            request_id=request_id,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
        )

        self.requests.append(cost_record)
        self._update_metrics(cost_record)

        return cost_record

    def _update_metrics(self, cost_record: ProviderCost) -> None:
        """Update provider metrics after recording a request."""
        metrics = self._metrics[cost_record.provider]

        metrics.total_requests += 1
        if cost_record.status == "success":
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1

        metrics.total_cost_usd += cost_record.cost_usd
        metrics.total_input_tokens += cost_record.token_usage.input_tokens
        metrics.total_output_tokens += cost_record.token_usage.output_tokens
        metrics.total_cached_tokens += cost_record.token_usage.cached_tokens
        metrics.total_duration_ms += cost_record.duration_ms

        # Track model usage
        if cost_record.model not in metrics.models_used:
            metrics.models_used[cost_record.model] = 0
            metrics.cost_by_model[cost_record.model] = 0.0

        metrics.models_used[cost_record.model] += 1
        metrics.cost_by_model[cost_record.model] += cost_record.cost_usd

        # Calculate averages
        if metrics.total_requests > 0:
            metrics.avg_cost_per_request = (
                metrics.total_cost_usd / metrics.total_requests
            )
            metrics.avg_tokens_per_request = (
                metrics.total_tokens // metrics.total_requests
            )
            metrics.error_rate = metrics.failed_requests / metrics.total_requests

        # Track cost per token bounds
        if cost_record.token_usage.total_tokens > 0:
            cost_per_token = cost_record.cost_usd / cost_record.token_usage.total_tokens
            metrics.min_cost_per_token = min(
                metrics.min_cost_per_token, cost_per_token
            )
            metrics.max_cost_per_token = max(
                metrics.max_cost_per_token, cost_per_token
            )

    def get_provider_metrics(
        self, provider: ProviderType
    ) -> ProviderMetrics:
        """Get metrics for a specific provider."""
        return self._metrics[provider]

    def get_all_metrics(self) -> Dict[str, ProviderMetrics]:
        """Get metrics for all providers."""
        return {
            provider.value: metrics
            for provider, metrics in self._metrics.items()
        }

    def get_total_cost(self) -> float:
        """Get total cost across all providers."""
        return sum(metrics.total_cost_usd for metrics in self._metrics.values())

    def get_total_tokens(self) -> int:
        """Get total tokens across all providers."""
        return sum(metrics.total_tokens for metrics in self._metrics.values())

    def get_requests_by_provider(
        self, provider: ProviderType
    ) -> List[ProviderCost]:
        """Get all requests for a specific provider."""
        return [req for req in self.requests if req.provider == provider]

    def get_requests_by_model(self, model: str) -> List[ProviderCost]:
        """Get all requests for a specific model."""
        return [req for req in self.requests if req.model == model]

    def get_most_expensive_requests(self, limit: int = 10) -> List[ProviderCost]:
        """Get the most expensive requests across all providers."""
        sorted_requests = sorted(
            self.requests, key=lambda r: r.cost_usd, reverse=True
        )
        return sorted_requests[:limit]

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return {
            provider.value: metrics.total_cost_usd
            for provider, metrics in self._metrics.items()
            if metrics.total_requests > 0
        }

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model."""
        model_costs: Dict[str, float] = defaultdict(float)
        for req in self.requests:
            model_costs[req.model] += req.cost_usd
        return dict(model_costs)

    def get_cheapest_provider(self) -> Optional[Tuple[ProviderType, float]]:
        """Get the provider with lowest cost per token."""
        providers_with_requests = [
            (provider, metrics)
            for provider, metrics in self._metrics.items()
            if metrics.total_requests > 0
        ]

        if not providers_with_requests:
            return None

        return min(
            providers_with_requests,
            key=lambda x: x[1].cost_per_token,
        )[0], min(
            providers_with_requests, key=lambda x: x[1].cost_per_token
        )[1].cost_per_token

    def get_fastest_provider(self) -> Optional[Tuple[ProviderType, float]]:
        """Get the provider with lowest average response time."""
        providers_with_requests = [
            (provider, metrics)
            for provider, metrics in self._metrics.items()
            if metrics.total_requests > 0
        ]

        if not providers_with_requests:
            return None

        best = min(
            providers_with_requests,
            key=lambda x: x[1].total_duration_ms / max(1, x[1].total_requests),
        )
        return best[0], best[1].total_duration_ms / max(1, best[1].total_requests)

    def get_comparison(self) -> Dict:
        """Get comprehensive provider comparison."""
        metrics_list = [
            (provider.value, metrics)
            for provider, metrics in self._metrics.items()
            if metrics.total_requests > 0
        ]

        if not metrics_list:
            return {}

        return {
            "summary": {
                "total_providers": len(metrics_list),
                "total_requests": sum(m[1].total_requests for m in metrics_list),
                "total_cost": round(self.get_total_cost(), 6),
                "total_tokens": self.get_total_tokens(),
            },
            "by_provider": {
                name: metrics.to_dict()
                for name, metrics in metrics_list
            },
            "rankings": {
                "cheapest_provider": self.get_cheapest_provider()[0].value
                if self.get_cheapest_provider()
                else None,
                "cheapest_cost_per_token": round(
                    self.get_cheapest_provider()[1], 8
                )
                if self.get_cheapest_provider()
                else None,
                "fastest_provider": self.get_fastest_provider()[0].value
                if self.get_fastest_provider()
                else None,
                "fastest_avg_ms": round(
                    self.get_fastest_provider()[1], 2
                )
                if self.get_fastest_provider()
                else None,
            },
        }

    def get_cost_trend(
        self, period: str = "hourly"
    ) -> Dict[str, Dict[str, float]]:
        """Get cost trends over time."""
        trends: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        for req in self.requests:
            if period == "hourly":
                key = req.timestamp.strftime("%Y-%m-%d %H:00:00")
            elif period == "daily":
                key = req.timestamp.strftime("%Y-%m-%d")
            elif period == "weekly":
                key = req.timestamp.strftime("Week %W, %Y")
            else:
                key = req.timestamp.isoformat()

            trends[key][req.provider.value] += req.cost_usd

        return dict(trends)

    def get_efficiency_metrics(self) -> Dict:
        """Calculate efficiency metrics across all providers."""
        if not self.requests:
            return {}

        total_cost = self.get_total_cost()
        total_tokens = self.get_total_tokens()
        successful = sum(
            1 for req in self.requests if req.status == "success"
        )

        return {
            "total_requests": len(self.requests),
            "successful_requests": successful,
            "success_rate": successful / len(self.requests) if self.requests else 0.0,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "avg_cost_per_token": round(total_cost / total_tokens, 8)
            if total_tokens > 0
            else 0.0,
            "avg_cost_per_request": round(total_cost / len(self.requests), 6),
            "avg_tokens_per_request": total_tokens // len(self.requests)
            if self.requests
            else 0,
        }

    def export_to_json(self) -> str:
        """Export all data to JSON format."""
        return json.dumps({
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat(),
            "session_duration_ms": int(
                (datetime.now() - self.session_start).total_seconds() * 1000
            ),
            "metrics": {
                provider.value: metrics.to_dict()
                for provider, metrics in self._metrics.items()
            },
            "efficiency": self.get_efficiency_metrics(),
            "comparison": self.get_comparison(),
            "cost_trends": self.get_cost_trend("daily"),
        }, indent=2)

    def export_requests_to_json(self) -> str:
        """Export detailed request records to JSON."""
        return json.dumps({
            "session_id": self.session_id,
            "request_count": len(self.requests),
            "requests": [req.to_dict() for req in self.requests],
        }, indent=2)
