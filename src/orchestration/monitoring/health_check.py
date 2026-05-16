"""
Health Check — Endpoint for Orchestrator health status.

Provides a composable health check system where individual checks
can be registered and queried. Suitable for Kubernetes liveness/readiness
probes and load balancer health checks.

Usage:
    health = HealthCheck()

    @health.register("queue")
    def check_queue():
        # return True if healthy, False or raise if not
        return queue_depth < 1000

    status = health.check()
    print(status.healthy)   # True/False
    print(status.to_dict()) # Full status dict
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any


class HealthStatus(Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
        }


@dataclass
class HealthReport:
    """Aggregated health report from all checks."""
    status: HealthStatus
    checks: List[CheckResult]
    timestamp: float = field(default_factory=time.time)
    version: str = "1.0"

    @property
    def healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "healthy": self.healthy,
            "timestamp": self.timestamp,
            "version": self.version,
            "checks": [c.to_dict() for c in self.checks],
        }


class HealthCheck:
    """
    Composable health check system.

    Register named check functions that return True (healthy),
    False (unhealthy), or raise an exception (unhealthy).
    """

    def __init__(self):
        self._checks: Dict[str, Callable] = {}

    def register(self, name: str, critical: bool = True) -> Callable:
        """
        Decorator to register a health check function.

        Args:
            name: Check name
            critical: If True, failure marks overall status UNHEALTHY.
                      If False, failure marks DEGRADED.
        """
        def decorator(fn: Callable) -> Callable:
            self._checks[name] = (fn, critical)
            return fn
        return decorator

    def add_check(self, name: str, fn: Callable, critical: bool = True) -> None:
        """Register a health check function directly."""
        self._checks[name] = (fn, critical)

    def check(self) -> HealthReport:
        """
        Run all registered health checks.

        Returns:
            HealthReport with status and individual check results.
        """
        results: List[CheckResult] = []
        overall = HealthStatus.HEALTHY

        for name, (fn, critical) in self._checks.items():
            start = time.time()
            try:
                result = fn()
                duration_ms = (time.time() - start) * 1000
                if result is False:
                    status = HealthStatus.UNHEALTHY if critical else HealthStatus.DEGRADED
                    message = f"Check '{name}' returned False"
                else:
                    status = HealthStatus.HEALTHY
                    message = "OK"
                    # Support returning a dict with details
                    details = result if isinstance(result, dict) else {}
                results.append(CheckResult(
                    name=name,
                    status=status,
                    message=message,
                    duration_ms=duration_ms,
                    details=details if isinstance(result, dict) else {},
                ))
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                status = HealthStatus.UNHEALTHY if critical else HealthStatus.DEGRADED
                results.append(CheckResult(
                    name=name,
                    status=status,
                    message=str(e),
                    duration_ms=duration_ms,
                ))

            # Update overall status
            if results[-1].status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
            elif results[-1].status == HealthStatus.DEGRADED and overall == HealthStatus.HEALTHY:
                overall = HealthStatus.DEGRADED

        return HealthReport(status=overall, checks=results)

    def liveness(self) -> bool:
        """Simple liveness check — True if process is running."""
        return True

    def readiness(self) -> bool:
        """Readiness check — True if all critical checks pass."""
        report = self.check()
        return report.status != HealthStatus.UNHEALTHY
