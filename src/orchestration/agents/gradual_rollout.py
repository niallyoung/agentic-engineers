"""
Gradual Rollout System for Orchestrator.

Provides a production-safe 5-stage rollout mechanism that deploys changes
incrementally with health checks, automatic rollback, and manual controls.

Stages:
    STAGE_10  → 10% traffic
    STAGE_25  → 25% traffic
    STAGE_50  → 50% traffic
    STAGE_75  → 75% traffic
    STAGE_100 → 100% traffic

Features:
- Deterministic traffic sampling based on task ID (MD5 hash)
- Health check evaluation at each stage before progression
- Automatic rollback if error rate or quality score thresholds are breached
- Manual controls: pause, resume, advance, rollback
- Feature flag support via environment variables
- Comprehensive audit trail for all rollout decisions
- Integration with monitoring system (metrics, alerts, SLOs)
- Integration with dry-run and shadow mode

Environment Variables:
    ROLLOUT_ENABLED         — "true"/"false" (default: "true")
    ROLLOUT_STAGE           — Override stage: "10","25","50","75","100","0" (0=disabled)
    ROLLOUT_PAUSED          — "true"/"false" (default: "false")
    ROLLOUT_AUTO_ADVANCE    — "true"/"false" (default: "true")
    ROLLOUT_ERROR_THRESHOLD — Max error rate before rollback (default: "0.05")
    ROLLOUT_QUALITY_MIN     — Min quality score before rollback (default: "0.80")
    ROLLOUT_MIN_SAMPLES     — Min samples before health check (default: "20")
    ROLLOUT_AUDIT_DIR       — Directory for audit logs (default: "artifacts/rollout")
"""

import os
import json
import hashlib
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RolloutStage(Enum):
    """5-stage rollout progression."""
    DISABLED = 0      # Rollout disabled — all traffic uses old path
    STAGE_10 = 10     # 10% traffic on new path
    STAGE_25 = 25     # 25% traffic on new path
    STAGE_50 = 50     # 50% traffic on new path
    STAGE_75 = 75     # 75% traffic on new path
    STAGE_100 = 100   # 100% traffic on new path (fully rolled out)

    @classmethod
    def progression(cls) -> List["RolloutStage"]:
        """Ordered list of active stages (excluding DISABLED)."""
        return [cls.STAGE_10, cls.STAGE_25, cls.STAGE_50, cls.STAGE_75, cls.STAGE_100]

    def next_stage(self) -> Optional["RolloutStage"]:
        """Return the next stage in progression, or None if fully rolled out."""
        stages = self.progression()
        if self == RolloutStage.DISABLED:
            return stages[0]
        try:
            idx = stages.index(self)
            return stages[idx + 1] if idx + 1 < len(stages) else None
        except ValueError:
            return None

    def prev_stage(self) -> Optional["RolloutStage"]:
        """Return the previous stage, or DISABLED if at stage 10."""
        stages = self.progression()
        if self == RolloutStage.DISABLED:
            return None
        try:
            idx = stages.index(self)
            return stages[idx - 1] if idx > 0 else RolloutStage.DISABLED
        except ValueError:
            return RolloutStage.DISABLED


class RolloutAction(Enum):
    """Actions that can be taken on the rollout."""
    ADVANCE   = "advance"    # Move to next stage
    ROLLBACK  = "rollback"   # Move to previous stage (or DISABLED)
    PAUSE     = "pause"      # Pause at current stage
    RESUME    = "resume"     # Resume from paused state
    OVERRIDE  = "override"   # Manual stage override
    DISABLE   = "disable"    # Disable rollout entirely


class RolloutDecisionReason(Enum):
    """Why a rollout decision was made."""
    HEALTH_CHECK_PASSED   = "health_check_passed"
    HEALTH_CHECK_FAILED   = "health_check_failed"
    ERROR_RATE_EXCEEDED   = "error_rate_exceeded"
    QUALITY_SCORE_LOW     = "quality_score_low"
    INSUFFICIENT_SAMPLES  = "insufficient_samples"
    MANUAL_ADVANCE        = "manual_advance"
    MANUAL_ROLLBACK       = "manual_rollback"
    MANUAL_PAUSE          = "manual_pause"
    MANUAL_RESUME         = "manual_resume"
    MANUAL_OVERRIDE       = "manual_override"
    MANUAL_DISABLE        = "manual_disable"
    AUTO_ADVANCE          = "auto_advance"
    INITIALIZATION        = "initialization"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RolloutHealthSnapshot:
    """Health metrics snapshot at a point in time."""
    timestamp: str
    stage: int
    total_samples: int
    error_rate: float          # 0.0–1.0
    quality_score: float       # 0.0–1.0
    avg_latency_ms: float
    p95_latency_ms: float
    is_healthy: bool
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RolloutDecision:
    """Audit record for a rollout decision."""
    timestamp: str
    action: str                 # RolloutAction.value
    reason: str                 # RolloutDecisionReason.value
    from_stage: int
    to_stage: int
    health_snapshot: Optional[Dict[str, Any]] = None
    operator: str = "system"    # "system" or human operator ID
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RolloutConfig:
    """Configuration for the rollout manager."""
    error_threshold: float = 0.05    # Max acceptable error rate
    quality_min: float = 0.80        # Min acceptable quality score
    min_samples: int = 20            # Min samples before health evaluation
    auto_advance: bool = True        # Automatically advance stages on health pass
    audit_dir: str = "artifacts/rollout"

    @classmethod
    def from_env(cls) -> "RolloutConfig":
        """Load configuration from environment variables."""
        return cls(
            error_threshold=float(os.environ.get("ROLLOUT_ERROR_THRESHOLD", "0.05")),
            quality_min=float(os.environ.get("ROLLOUT_QUALITY_MIN", "0.80")),
            min_samples=int(os.environ.get("ROLLOUT_MIN_SAMPLES", "20")),
            auto_advance=os.environ.get("ROLLOUT_AUTO_ADVANCE", "true").lower() == "true",
            audit_dir=os.environ.get("ROLLOUT_AUDIT_DIR", "artifacts/rollout"),
        )


# ---------------------------------------------------------------------------
# Traffic Sampler
# ---------------------------------------------------------------------------

class TrafficSampler:
    """
    Deterministic traffic sampler based on task ID.

    Uses MD5 hash of task_id to produce a stable [0, 100) bucket.
    The same task_id always maps to the same bucket, ensuring consistent
    routing across multiple calls.
    """

    @staticmethod
    def sample(task_id: str, percentage: int) -> bool:
        """
        Return True if this task_id falls within the rollout percentage.

        Args:
            task_id: Unique task identifier.
            percentage: Traffic percentage (0–100).

        Returns:
            True if the task should use the new code path.
        """
        if percentage <= 0:
            return False
        if percentage >= 100:
            return True
        digest = hashlib.md5(task_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100  # 0–99
        return bucket < percentage

    @staticmethod
    def bucket(task_id: str) -> int:
        """Return the deterministic bucket (0–99) for a task_id."""
        digest = hashlib.md5(task_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100


# ---------------------------------------------------------------------------
# Health Check Evaluator
# ---------------------------------------------------------------------------

class HealthCheckEvaluator:
    """
    Evaluates rollout health based on accumulated metrics.

    Thresholds (configurable via RolloutConfig):
        error_rate  <= config.error_threshold  (default 5%)
        quality     >= config.quality_min      (default 80%)
        samples     >= config.min_samples      (default 20)
    """

    def __init__(self, config: RolloutConfig):
        self.config = config

    def evaluate(
        self,
        stage: RolloutStage,
        metrics: "StageMetrics",
    ) -> RolloutHealthSnapshot:
        """
        Evaluate health for the current stage.

        Args:
            stage: Current rollout stage.
            metrics: Accumulated metrics for this stage.

        Returns:
            RolloutHealthSnapshot with is_healthy flag and failure reasons.
        """
        failure_reasons: List[str] = []

        total = metrics.total_tasks
        errors = metrics.error_tasks
        quality_sum = metrics.quality_score_sum
        latencies = metrics.latency_samples

        error_rate = (errors / total) if total > 0 else 0.0
        quality_score = (quality_sum / total) if total > 0 else 0.0
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
        p95_latency = self._p95(latencies)

        # Check minimum samples
        if total < self.config.min_samples:
            failure_reasons.append(
                f"Insufficient samples: {total} < {self.config.min_samples}"
            )

        # Check error rate
        if error_rate > self.config.error_threshold:
            failure_reasons.append(
                f"Error rate {error_rate:.1%} exceeds threshold {self.config.error_threshold:.1%}"
            )

        # Check quality score
        if total >= self.config.min_samples and quality_score < self.config.quality_min:
            failure_reasons.append(
                f"Quality score {quality_score:.2f} below minimum {self.config.quality_min:.2f}"
            )

        return RolloutHealthSnapshot(
            timestamp=_now(),
            stage=stage.value,
            total_samples=total,
            error_rate=error_rate,
            quality_score=quality_score,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            is_healthy=len(failure_reasons) == 0,
            failure_reasons=failure_reasons,
        )

    @staticmethod
    def _p95(values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]


# ---------------------------------------------------------------------------
# Stage Metrics
# ---------------------------------------------------------------------------

@dataclass
class StageMetrics:
    """Accumulated metrics for a single rollout stage."""
    stage: int
    total_tasks: int = 0
    error_tasks: int = 0
    quality_score_sum: float = 0.0
    latency_samples: List[float] = field(default_factory=list)

    def record(self, *, error: bool, quality_score: float, latency_ms: float) -> None:
        """Record a single task outcome."""
        self.total_tasks += 1
        if error:
            self.error_tasks += 1
        self.quality_score_sum += quality_score
        self.latency_samples.append(latency_ms)

    @property
    def error_rate(self) -> float:
        return (self.error_tasks / self.total_tasks) if self.total_tasks > 0 else 0.0

    @property
    def avg_quality(self) -> float:
        return (self.quality_score_sum / self.total_tasks) if self.total_tasks > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "total_tasks": self.total_tasks,
            "error_tasks": self.error_tasks,
            "error_rate": self.error_rate,
            "avg_quality": self.avg_quality,
            "latency_sample_count": len(self.latency_samples),
        }


# ---------------------------------------------------------------------------
# RolloutManager
# ---------------------------------------------------------------------------

class RolloutManager:
    """
    Production-safe gradual rollout manager.

    Orchestrates a 5-stage rollout with:
    - Deterministic traffic sampling
    - Health check evaluation
    - Automatic rollback on threshold breach
    - Manual controls (pause, resume, advance, rollback, override)
    - Full audit trail

    Usage:
        manager = RolloutManager.from_env()

        # Check if a task should use the new code path
        if manager.should_use_new_path(task_id):
            result = new_implementation(task)
        else:
            result = old_implementation(task)

        # Record outcome for health tracking
        manager.record_outcome(task_id, error=False, quality_score=0.92, latency_ms=150)

        # Evaluate health and potentially advance stage
        manager.evaluate_and_advance()
    """

    def __init__(
        self,
        config: Optional[RolloutConfig] = None,
        initial_stage: RolloutStage = RolloutStage.DISABLED,
        enabled: bool = True,
    ):
        self.config = config or RolloutConfig()
        self._stage = initial_stage
        self._enabled = enabled
        self._paused = False
        self._lock = threading.Lock()

        # Per-stage metrics
        self._stage_metrics: Dict[int, StageMetrics] = {
            s.value: StageMetrics(stage=s.value) for s in RolloutStage
        }

        # Audit trail
        self._audit_trail: List[RolloutDecision] = []

        # Health evaluator
        self._health_evaluator = HealthCheckEvaluator(self.config)

        # Audit directory
        self._audit_dir = Path(self.config.audit_dir)
        self._audit_dir.mkdir(parents=True, exist_ok=True)

        # Log initialization
        self._record_decision(
            action=RolloutAction.OVERRIDE,
            reason=RolloutDecisionReason.INITIALIZATION,
            from_stage=RolloutStage.DISABLED,
            to_stage=self._stage,
            notes=f"RolloutManager initialized. enabled={enabled}",
        )

        logger.info(
            f"RolloutManager initialized: stage={self._stage.name}, "
            f"enabled={enabled}, auto_advance={self.config.auto_advance}"
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "RolloutManager":
        """Create RolloutManager from environment variables."""
        config = RolloutConfig.from_env()
        enabled = os.environ.get("ROLLOUT_ENABLED", "true").lower() == "true"
        paused = os.environ.get("ROLLOUT_PAUSED", "false").lower() == "true"

        stage_val = int(os.environ.get("ROLLOUT_STAGE", "0"))
        try:
            stage = RolloutStage(stage_val)
        except ValueError:
            logger.warning(f"Invalid ROLLOUT_STAGE={stage_val}, defaulting to DISABLED")
            stage = RolloutStage.DISABLED

        manager = cls(config=config, initial_stage=stage, enabled=enabled)
        if paused:
            manager._paused = True
        return manager

    # ------------------------------------------------------------------
    # Core routing
    # ------------------------------------------------------------------

    def should_use_new_path(self, task_id: str) -> bool:
        """
        Determine if this task should use the new code path.

        Args:
            task_id: Unique task identifier for deterministic sampling.

        Returns:
            True if the task should use the new implementation.
        """
        with self._lock:
            if not self._enabled:
                return False
            if self._stage == RolloutStage.DISABLED:
                return False
            return TrafficSampler.sample(task_id, self._stage.value)

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        task_id: str,
        *,
        error: bool,
        quality_score: float = 1.0,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Record the outcome of a task for health tracking.

        Only records outcomes for tasks that were routed to the new path.

        Args:
            task_id: Task identifier.
            error: Whether the task resulted in an error.
            quality_score: Quality score (0.0–1.0).
            latency_ms: Task latency in milliseconds.
        """
        with self._lock:
            if not self._enabled or self._stage == RolloutStage.DISABLED:
                return
            # Only record if this task was sampled
            if not TrafficSampler.sample(task_id, self._stage.value):
                return
            metrics = self._stage_metrics[self._stage.value]
            metrics.record(error=error, quality_score=quality_score, latency_ms=latency_ms)

        # Check for immediate rollback triggers (outside lock to avoid deadlock)
        self._check_auto_rollback()

    # ------------------------------------------------------------------
    # Health evaluation & auto-advance
    # ------------------------------------------------------------------

    def evaluate_health(self) -> RolloutHealthSnapshot:
        """Evaluate health for the current stage."""
        with self._lock:
            stage = self._stage
            metrics = self._stage_metrics[stage.value]
        return self._health_evaluator.evaluate(stage, metrics)

    def evaluate_and_advance(self) -> Optional[RolloutStage]:
        """
        Evaluate health and advance to the next stage if healthy.

        Returns:
            New stage if advanced, None if no change.
        """
        if not self.config.auto_advance:
            return None

        with self._lock:
            if self._paused or not self._enabled:
                return None
            stage = self._stage
            if stage == RolloutStage.STAGE_100:
                return None  # Already fully rolled out
            metrics = self._stage_metrics[stage.value]

        snapshot = self._health_evaluator.evaluate(stage, metrics)

        if snapshot.is_healthy:
            next_stage = stage.next_stage()
            if next_stage is not None:
                self._transition(
                    action=RolloutAction.ADVANCE,
                    reason=RolloutDecisionReason.AUTO_ADVANCE,
                    to_stage=next_stage,
                    health_snapshot=snapshot,
                )
                return next_stage
        else:
            # Check if we need to rollback due to threshold breach
            self._check_auto_rollback(snapshot=snapshot)

        return None

    def _check_auto_rollback(self, snapshot: Optional[RolloutHealthSnapshot] = None) -> None:
        """Check if automatic rollback is needed."""
        with self._lock:
            stage = self._stage
            if stage == RolloutStage.DISABLED:
                return
            metrics = self._stage_metrics[stage.value]

        if snapshot is None:
            snapshot = self._health_evaluator.evaluate(stage, metrics)

        # Only trigger rollback on hard threshold breaches (not insufficient samples)
        if snapshot.total_samples < self.config.min_samples:
            return

        reason = None
        if snapshot.error_rate > self.config.error_threshold:
            reason = RolloutDecisionReason.ERROR_RATE_EXCEEDED
        elif snapshot.quality_score < self.config.quality_min:
            reason = RolloutDecisionReason.QUALITY_SCORE_LOW

        if reason is not None:
            prev = stage.prev_stage()
            target = prev if prev is not None else RolloutStage.DISABLED
            self._transition(
                action=RolloutAction.ROLLBACK,
                reason=reason,
                to_stage=target,
                health_snapshot=snapshot,
            )

    # ------------------------------------------------------------------
    # Manual controls
    # ------------------------------------------------------------------

    def pause(self, operator: str = "operator") -> None:
        """Pause the rollout at the current stage."""
        with self._lock:
            self._paused = True
        self._record_decision(
            action=RolloutAction.PAUSE,
            reason=RolloutDecisionReason.MANUAL_PAUSE,
            from_stage=self._stage,
            to_stage=self._stage,
            operator=operator,
            notes="Rollout paused by operator.",
        )
        logger.info(f"Rollout paused by {operator} at stage {self._stage.name}")

    def resume(self, operator: str = "operator") -> None:
        """Resume a paused rollout."""
        with self._lock:
            self._paused = False
        self._record_decision(
            action=RolloutAction.RESUME,
            reason=RolloutDecisionReason.MANUAL_RESUME,
            from_stage=self._stage,
            to_stage=self._stage,
            operator=operator,
            notes="Rollout resumed by operator.",
        )
        logger.info(f"Rollout resumed by {operator} at stage {self._stage.name}")

    def advance(self, operator: str = "operator") -> Optional[RolloutStage]:
        """Manually advance to the next stage (bypasses health check)."""
        with self._lock:
            current = self._stage
        next_stage = current.next_stage()
        if next_stage is None:
            logger.info("Rollout already at STAGE_100, cannot advance further.")
            return None
        self._transition(
            action=RolloutAction.ADVANCE,
            reason=RolloutDecisionReason.MANUAL_ADVANCE,
            to_stage=next_stage,
            operator=operator,
        )
        return next_stage

    def rollback(self, operator: str = "operator") -> RolloutStage:
        """Manually rollback to the previous stage (or DISABLED)."""
        with self._lock:
            current = self._stage
        prev = current.prev_stage()
        target = prev if prev is not None else RolloutStage.DISABLED
        self._transition(
            action=RolloutAction.ROLLBACK,
            reason=RolloutDecisionReason.MANUAL_ROLLBACK,
            to_stage=target,
            operator=operator,
        )
        return target

    def override_stage(self, stage: RolloutStage, operator: str = "operator") -> None:
        """Override the current stage directly."""
        with self._lock:
            current = self._stage
        self._transition(
            action=RolloutAction.OVERRIDE,
            reason=RolloutDecisionReason.MANUAL_OVERRIDE,
            to_stage=stage,
            operator=operator,
            notes=f"Stage overridden from {current.name} to {stage.name}",
        )

    def disable(self, operator: str = "operator") -> None:
        """Disable the rollout entirely (all traffic to old path)."""
        with self._lock:
            current = self._stage
        self._transition(
            action=RolloutAction.DISABLE,
            reason=RolloutDecisionReason.MANUAL_DISABLE,
            to_stage=RolloutStage.DISABLED,
            operator=operator,
            notes="Rollout disabled by operator.",
        )

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def stage(self) -> RolloutStage:
        with self._lock:
            return self._stage

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def get_stage_metrics(self, stage: Optional[RolloutStage] = None) -> StageMetrics:
        """Return metrics for a specific stage (default: current stage)."""
        with self._lock:
            s = stage or self._stage
            return self._stage_metrics[s.value]

    def get_audit_trail(self) -> List[RolloutDecision]:
        """Return a copy of the audit trail."""
        with self._lock:
            return list(self._audit_trail)

    def status(self) -> Dict[str, Any]:
        """Return a full status snapshot."""
        with self._lock:
            stage = self._stage
            paused = self._paused
            enabled = self._enabled
            metrics = self._stage_metrics[stage.value]

        snapshot = self._health_evaluator.evaluate(stage, metrics)
        return {
            "stage": stage.name,
            "stage_value": stage.value,
            "enabled": enabled,
            "paused": paused,
            "health": snapshot.to_dict(),
            "metrics": metrics.to_dict(),
            "audit_trail_length": len(self._audit_trail),
            "config": {
                "error_threshold": self.config.error_threshold,
                "quality_min": self.config.quality_min,
                "min_samples": self.config.min_samples,
                "auto_advance": self.config.auto_advance,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(
        self,
        action: RolloutAction,
        reason: RolloutDecisionReason,
        to_stage: RolloutStage,
        health_snapshot: Optional[RolloutHealthSnapshot] = None,
        operator: str = "system",
        notes: str = "",
    ) -> None:
        """Execute a stage transition and record it."""
        with self._lock:
            from_stage = self._stage
            self._stage = to_stage

        self._record_decision(
            action=action,
            reason=reason,
            from_stage=from_stage,
            to_stage=to_stage,
            health_snapshot=health_snapshot,
            operator=operator,
            notes=notes,
        )
        logger.info(
            f"Rollout transition: {from_stage.name} → {to_stage.name} "
            f"[{action.value}/{reason.value}] operator={operator}"
        )

    def _record_decision(
        self,
        action: RolloutAction,
        reason: RolloutDecisionReason,
        from_stage: RolloutStage,
        to_stage: RolloutStage,
        health_snapshot: Optional[RolloutHealthSnapshot] = None,
        operator: str = "system",
        notes: str = "",
    ) -> None:
        """Append a decision to the audit trail and persist to disk."""
        decision = RolloutDecision(
            timestamp=_now(),
            action=action.value,
            reason=reason.value,
            from_stage=from_stage.value,
            to_stage=to_stage.value,
            health_snapshot=health_snapshot.to_dict() if health_snapshot else None,
            operator=operator,
            notes=notes,
        )
        with self._lock:
            self._audit_trail.append(decision)

        self._persist_decision(decision)

    def _persist_decision(self, decision: RolloutDecision) -> None:
        """Write decision to audit log file."""
        try:
            log_file = self._audit_dir / "audit.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(decision.to_dict()) + "\n")
        except Exception as exc:
            logger.warning(f"Failed to persist rollout decision: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def create_rollout_manager(
    stage: int = 0,
    error_threshold: float = 0.05,
    quality_min: float = 0.80,
    min_samples: int = 20,
    auto_advance: bool = True,
    audit_dir: str = "artifacts/rollout",
    enabled: bool = True,
) -> RolloutManager:
    """
    Convenience factory for creating a RolloutManager with explicit parameters.

    Args:
        stage: Initial stage value (0, 10, 25, 50, 75, 100).
        error_threshold: Max acceptable error rate (default 5%).
        quality_min: Min acceptable quality score (default 80%).
        min_samples: Min samples before health evaluation (default 20).
        auto_advance: Automatically advance on health pass (default True).
        audit_dir: Directory for audit logs.
        enabled: Whether the rollout is enabled.

    Returns:
        Configured RolloutManager instance.
    """
    config = RolloutConfig(
        error_threshold=error_threshold,
        quality_min=quality_min,
        min_samples=min_samples,
        auto_advance=auto_advance,
        audit_dir=audit_dir,
    )
    try:
        initial_stage = RolloutStage(stage)
    except ValueError:
        raise ValueError(
            f"Invalid stage value: {stage}. Must be one of: "
            f"{[s.value for s in RolloutStage]}"
        )
    return RolloutManager(config=config, initial_stage=initial_stage, enabled=enabled)
